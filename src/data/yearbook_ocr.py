from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import cv2
from rapidocr_onnxruntime import RapidOCR

from src.config import DATA_RAW_DIR, INDICATORS, INDICATOR_NOTES, INDICATOR_UNITS, PROVINCES, REQUIRED_COLUMNS
from src.data.cleaner import clean_indicators
from src.data.fetcher import cache_path, template_path
from src.data.nbs_exports import load_exported_indicators
from src.data.nbs_yearbook import download_yearbook_tables
from src.data.nbs_yearbook import yearbook_year_for_data_year
import requests


@dataclass(frozen=True)
class ColumnSpec:
    source: str
    output: str
    x: float
    y_min: float
    y_max: float | None = None
    skip_rows: int = 0
    transform: str | None = None
    crop_right: int | None = None


SPECS = [
    ColumnSpec("gdp", "gdp", 140, 230),
    ColumnSpec("gdp", "gdp_growth", 1625, 230, transform="minus_100"),
    ColumnSpec("income", "income", 660, 210),
    ColumnSpec("retail", "retail", 410, 210),
    ColumnSpec("fiscal_revenue", "fiscal_revenue", 140, 240),
    # The yearbook publishes registered unemployed persons by province, not a clean rate.
    ColumnSpec("unemployment", "unemployment", 655, 140),
    # The available regional fixed-asset table is growth rate over previous year.
    ColumnSpec("fixed_invest", "fixed_invest", 140, 170),
    ColumnSpec("cpi", "cpi", 146, 260, crop_right=360),
]


def _specs_for_year(data_year: int) -> list[ColumnSpec]:
    specs = list(SPECS)
    if data_year >= 2024:
        specs = [
            ColumnSpec(**{**spec.__dict__, "x": 1698})
            if spec.source == "gdp" and spec.output == "gdp_growth"
            else ColumnSpec(**{**spec.__dict__, "x": 246, "y_min": 220})
            if spec.source == "unemployment" and spec.output == "unemployment"
            else spec
            for spec in specs
        ]
    return specs


def _number(text: str) -> float | None:
    cleaned = text.replace(",", "").replace("，", "").replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def _ocr_items(image_path: Path) -> list[dict[str, float | str]]:
    ocr = RapidOCR()
    result, _ = ocr(str(image_path))
    items = []
    for box, text, score in result or []:
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        value = _number(text)
        if value is None:
            continue
        items.append(
            {
                "text": text,
                "value": value,
                "score": float(score),
                "x": (min(xs) + max(xs)) / 2,
                "y": (min(ys) + max(ys)) / 2,
            }
        )
    return items


def _cluster_by_y(items: list[dict[str, float | str]], tolerance: float = 14) -> list[list[dict[str, float | str]]]:
    rows: list[list[dict[str, float | str]]] = []
    for item in sorted(items, key=lambda item: float(item["y"])):
        if not rows:
            rows.append([item])
            continue
        row_y = sum(float(row_item["y"]) for row_item in rows[-1]) / len(rows[-1])
        if abs(float(item["y"]) - row_y) <= tolerance:
            rows[-1].append(item)
        else:
            rows.append([item])
    return rows


def _image_for_spec(image_path: Path, spec: ColumnSpec) -> Path:
    if spec.crop_right is None:
        return image_path

    cropped_path = image_path.with_name(f"{image_path.stem}_{spec.output}_crop{image_path.suffix}")
    if cropped_path.exists():
        return cropped_path

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"无法读取图片: {image_path}")
    cropped = image[:, : spec.crop_right]
    cv2.imwrite(str(cropped_path), cropped)
    return cropped_path


def _extract_column(image_path: Path, spec: ColumnSpec) -> list[float]:
    image_path = _image_for_spec(image_path, spec)
    items = [
        item
        for item in _ocr_items(image_path)
        if float(item["y"]) >= spec.y_min
        and (spec.y_max is None or float(item["y"]) <= spec.y_max)
        and abs(float(item["x"]) - spec.x) <= 45
    ]
    rows = _cluster_by_y(items)
    values: list[float] = []
    for row in rows[spec.skip_rows :]:
        best = min(row, key=lambda item: abs(float(item["x"]) - spec.x))
        values.append(float(best["value"]))
    values = values[: len(PROVINCES)]

    if len(values) != len(PROVINCES):
        raise ValueError(f"{spec.source}.{spec.output} 只识别到 {len(values)} 个省份值")

    if spec.transform == "minus_100":
        values = [value - 100 for value in values]

    return values


def _ensure_employment_total_image(data_year: int, source_dir: Path) -> Path:
    path = source_dir / "employment_total.jpg"
    if path.exists():
        return path

    yearbook_year = yearbook_year_for_data_year(data_year)
    url = f"https://www.stats.gov.cn/sj/ndsj/{yearbook_year}/html/C04-03.jpg"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def _extract_employment_total(data_year: int, source_dir: Path) -> pd.Series:
    image_path = _ensure_employment_total_image(data_year, source_dir)
    values = _extract_column(
        image_path,
        ColumnSpec("employment_total", "employment_total", 150, 220),
    )
    return pd.Series(values, index=PROVINCES, name="employment_total")


def parse_yearbook_images(data_year: int = 2023, refresh_sources: bool = False) -> pd.DataFrame:
    source_dir = DATA_RAW_DIR / f"yearbook_{data_year}"
    if refresh_sources or not source_dir.exists():
        download_yearbook_tables(data_year, source_dir)

    rows = [{"province": province, "year": data_year} for province in PROVINCES]
    raw_df = pd.DataFrame(rows)

    for spec in _specs_for_year(data_year):
        image_path = source_dir / f"{spec.source}.jpg"
        if not image_path.exists():
            download_yearbook_tables(data_year, source_dir)
        raw_df[spec.output] = _extract_column(image_path, spec)

    exported = load_exported_indicators(data_year)
    if not exported.empty:
        raw_df = raw_df.set_index("province")
        for column in exported.columns:
            raw_df[column] = exported[column]
        raw_df = raw_df.reset_index()

    employment_total = _extract_employment_total(data_year, source_dir)
    raw_df = raw_df.set_index("province")
    unemployed = raw_df["unemployment"]
    raw_df["unemployment"] = unemployed / (employment_total + unemployed) * 100
    raw_df = raw_df.reset_index()

    raw_df = raw_df[REQUIRED_COLUMNS]
    raw_path = template_path(data_year)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    write_indicator_metadata(data_year, raw_path.with_name(f"province_indicators_{data_year}_metadata.csv"))

    cleaned = clean_indicators(raw_df, data_year)
    cached = cache_path(data_year)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(cached, encoding="utf-8-sig")
    write_indicator_metadata(data_year, cached.with_name(f"indicators_{data_year}_metadata.csv"))
    return cleaned


def write_indicator_metadata(data_year: int, path: Path) -> Path:
    rows = []
    for key, label in INDICATORS.items():
        note = INDICATOR_NOTES[key]
        if key == "unemployment" and data_year >= 2024:
            note = "失业相关人数/(就业人员+失业相关人数)*100。2024年分子为年末领取失业保险金人数，就业人员来自年鉴C04-03。"
        rows.append(
            {
                "column": key,
                "label": label,
                "unit": INDICATOR_UNITS[key],
                "note": note,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path
