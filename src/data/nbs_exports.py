from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import DATA_RAW_DIR, PROVINCES


NBS_EXPORTS_DIR = DATA_RAW_DIR / "nbs_exports"


def _export_path(filename: str) -> Path:
    organized = NBS_EXPORTS_DIR / filename
    if organized.exists():
        return organized
    return DATA_RAW_DIR / filename


def read_nbs_export(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\t,", engine="python", skiprows=2, encoding="utf-8-sig")
    df = df.dropna(axis=1, how="all")
    df.columns = [str(column).strip().replace("Unnamed: 0", "地区") for column in df.columns]
    if "地区" in df.columns:
        df = df[df["地区"].isin(PROVINCES)].copy()
    return df


def _load_year_column(rows: pd.DataFrame, filename: str, year: int, output_column: str) -> None:
    path = _export_path(filename)
    if not path.exists():
        return

    df = read_nbs_export(path).set_index("地区")
    year_column = f"{year}年"
    if year_column in df.columns:
        rows[output_column] = df[year_column]


def load_exported_indicators(year: int) -> pd.DataFrame:
    rows = pd.DataFrame({"province": PROVINCES}).set_index("province")

    _load_year_column(rows, "分省年度数据可支配收入.csv", year, "income")
    _load_year_column(rows, "分省年度数据消费支出.csv", year, "consumption_expenditure")
    _load_year_column(rows, "第一产业.csv", year, "primary_value")
    _load_year_column(rows, "第二产业.csv", year, "secondary_value")

    gdp_by_year = _export_path("按照年份的GDP.csv")
    if gdp_by_year.exists():
        df = read_nbs_export(gdp_by_year).set_index("地区")
        year_column = f"{year}年"
        if year_column in df.columns:
            rows["gdp"] = df[year_column]

    gdp_detail = _export_path(f"分省年度数据{year}.csv")
    if gdp_detail.exists():
        df = read_nbs_export(gdp_detail).set_index("地区")
        if "地区生产总值 (亿元)" in df.columns:
            rows["gdp"] = df["地区生产总值 (亿元)"]
        if "第一产业增加值 (亿元)" in df.columns:
            rows["primary_value"] = df["第一产业增加值 (亿元)"]
        if "第二产业增加值 (亿元)" in df.columns:
            rows["secondary_value"] = df["第二产业增加值 (亿元)"]
        if "第三产业增加值 (亿元)" in df.columns:
            rows["tertiary_value"] = df["第三产业增加值 (亿元)"]

    gdp_index = _export_path(f"分省年度数据指数{year}.csv")
    if gdp_index.exists():
        df = read_nbs_export(gdp_index).set_index("地区")
        if "地区生产总值指数 (上年=100)" in df.columns:
            rows["gdp_growth"] = df["地区生产总值指数 (上年=100)"] - 100

    cpi = _export_path("分省年度数据消费指数.csv")
    if cpi.exists() and year == 2024:
        df = read_nbs_export(cpi).set_index("地区")
        if "居民消费价格指数 (上年=100)" in df.columns:
            rows["cpi"] = df["居民消费价格指数 (上年=100)"]

    numeric = rows.apply(pd.to_numeric, errors="coerce")
    if {"gdp", "primary_value", "secondary_value"}.issubset(numeric.columns):
        rows["tertiary_value"] = numeric.get(
            "tertiary_value",
            numeric["gdp"] - numeric["primary_value"] - numeric["secondary_value"],
        ).fillna(numeric["gdp"] - numeric["primary_value"] - numeric["secondary_value"])

    numeric = rows.apply(pd.to_numeric, errors="coerce")
    if "gdp" in numeric.columns:
        for source, target in [
            ("primary_value", "primary_share"),
            ("secondary_value", "secondary_share"),
            ("tertiary_value", "tertiary_share"),
        ]:
            if source in numeric.columns:
                rows[target] = numeric[source] / numeric["gdp"] * 100

    return rows.dropna(axis=1, how="all")
