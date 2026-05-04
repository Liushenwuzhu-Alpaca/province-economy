from __future__ import annotations

import re

import pandas as pd

from src.config import INDICATORS, PROVINCE_ALIASES, PROVINCES


NUMERIC_COLUMNS = list(INDICATORS.keys())


def normalize_province_name(value: object) -> str:
    name = str(value).strip()
    return PROVINCE_ALIASES.get(name, name)


def coerce_number(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text in {"", "-", "--", "—", "nan", "None"}:
        return None
    text = text.replace(",", "").replace("，", "").replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def clean_indicators(raw_df: pd.DataFrame, year: int) -> pd.DataFrame:
    df = raw_df.copy()

    if "province" not in df.columns:
        raise ValueError("原始数据必须包含 province 列")
    if "year" in df.columns:
        df = df[df["year"].astype(str) == str(year)]

    df["province"] = df["province"].map(normalize_province_name)
    df = df.drop_duplicates(subset=["province"], keep="last")

    missing_columns = [column for column in NUMERIC_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"原始数据缺少指标列: {missing_columns}")

    for column in NUMERIC_COLUMNS:
        df[column] = df[column].map(coerce_number)

    # If users provide current and previous GDP, compute growth when the growth column is blank.
    if "gdp_prev" in df.columns:
        prev = df["gdp_prev"].map(coerce_number)
        calculated_growth = (df["gdp"] - prev) / prev * 100
        df["gdp_growth"] = df["gdp_growth"].fillna(calculated_growth)

    df = df.set_index("province").reindex(PROVINCES)
    df.index.name = "province"

    missing_provinces = df[df[NUMERIC_COLUMNS].isna().all(axis=1)].index.tolist()
    if missing_provinces:
        raise ValueError(f"缺少这些省份的数据: {missing_provinces}")

    for column in NUMERIC_COLUMNS:
        if df[column].isna().all():
            raise ValueError(f"{column} 整列为空，无法填补")
        df[column] = df[column].fillna(df[column].median())

    return df[NUMERIC_COLUMNS].astype(float)

