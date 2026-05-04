from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import (
    DATA_CACHE_DIR,
    DATA_RAW_DIR,
    INDICATORS,
    INDICATOR_NOTES,
    INDICATOR_UNITS,
    PROVINCES,
    REQUIRED_COLUMNS,
)
from src.data.cleaner import clean_indicators
from src.data.nbs_exports import load_exported_indicators


def template_path(year: int) -> Path:
    return DATA_RAW_DIR / "ocr_outputs" / f"province_indicators_{year}.csv"


def cache_path(year: int) -> Path:
    return DATA_CACHE_DIR / f"indicators_{year}.csv"


def metadata_path(year: int) -> Path:
    return DATA_CACHE_DIR / f"indicators_{year}_metadata.csv"


def write_metadata(year: int, path: Path | None = None) -> Path:
    output_path = path or metadata_path(year)
    rows = []
    for key, label in INDICATORS.items():
        note = INDICATOR_NOTES[key]
        if key == "unemployment" and year >= 2024:
            note = "失业相关人数/(就业人员+失业相关人数)*100。2024年分子为年末领取失业保险金人数，就业人员来自年鉴C04-03。"
        rows.append(
            {
                "column": key,
                "label": label,
                "unit": INDICATOR_UNITS[key],
                "note": note,
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def create_template(year: int, path: Path | None = None) -> Path:
    output_path = path or template_path(year)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [{"province": province, "year": year, **{key: "" for key in INDICATORS}} for province in PROVINCES]
    pd.DataFrame(rows, columns=REQUIRED_COLUMNS).to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def find_raw_file(year: int) -> Path | None:
    candidates = [
        DATA_RAW_DIR / "ocr_outputs" / f"province_indicators_{year}.csv",
        DATA_RAW_DIR / "ocr_outputs" / "province_indicators.csv",
        DATA_RAW_DIR / f"province_indicators_{year}.csv",
        DATA_RAW_DIR / "province_indicators.csv",
    ]
    return next((path for path in candidates if path.exists()), None)


def get_indicators(year: int = 2023, refresh: bool = False) -> pd.DataFrame:
    """
    Return cleaned 31-province indicators.

    Data source policy:
    1. read data_cache/indicators_{year}.csv when available;
    2. otherwise read data/raw/province_indicators_{year}.csv;
    3. create an empty template and raise a clear error if no raw CSV exists.
    """
    DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cached = cache_path(year)
    if cached.exists() and not refresh:
        cached_df = pd.read_csv(cached, index_col="province")
        if set(INDICATORS).issubset(cached_df.columns):
            return cached_df

    raw_path = find_raw_file(year)
    if raw_path is None:
        created = create_template(year)
        raise FileNotFoundError(
            f"没有找到原始数据 CSV，已生成模板: {created}. "
            "请按列填入国家统计局/统计年鉴整理的数据后重新运行。"
        )

    raw_df = pd.read_csv(raw_path)
    exported = load_exported_indicators(year)
    if not exported.empty:
        raw_df = raw_df.set_index("province")
        for column in exported.columns:
            raw_df[column] = exported[column]
        raw_df = raw_df.reset_index()

    cleaned = clean_indicators(raw_df, year)
    cleaned.to_csv(cached, encoding="utf-8-sig")
    write_metadata(year)
    return cleaned
