from __future__ import annotations

import pandas as pd

from src.config import INDICATORS, PROVINCES
from src.data.cleaner import normalize_province_name
from src.data.fetcher import get_indicators


def normalize_province_column(df: pd.DataFrame) -> pd.Series:
    if "province" in df.columns:
        values = df["province"]
    else:
        values = pd.Series(df.index, index=df.index)
    return values.map(normalize_province_name)


def missing_value_report(df: pd.DataFrame) -> pd.DataFrame:
    total_rows = len(df)
    rows = []
    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        rows.append(
            {
                "column": column,
                "missing_count": missing_count,
                "missing_rate": missing_count / total_rows if total_rows else 0,
            }
        )
    return pd.DataFrame(rows)


def province_coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    provinces = normalize_province_column(df)
    observed = set(provinces.dropna())
    expected = set(PROVINCES)
    duplicate_count = int(provinces.duplicated().sum())

    return pd.DataFrame(
        [
            {
                "check": "province_count",
                "status": "ok" if len(observed) == len(expected) else "warning",
                "detail": f"{len(observed)}/{len(expected)} provinces found",
            },
            {
                "check": "missing_provinces",
                "status": "ok" if expected <= observed else "error",
                "detail": "、".join(province for province in PROVINCES if province not in observed),
            },
            {
                "check": "unexpected_provinces",
                "status": "ok" if observed <= expected else "warning",
                "detail": "、".join(sorted(observed - expected)),
            },
            {
                "check": "duplicate_provinces",
                "status": "ok" if duplicate_count == 0 else "warning",
                "detail": str(duplicate_count),
            },
        ]
    )


def indicator_column_report(df: pd.DataFrame) -> pd.DataFrame:
    expected_columns = list(INDICATORS)
    missing_columns = [column for column in expected_columns if column not in df.columns]
    extra_columns = [column for column in df.columns if column not in expected_columns and column != "province"]

    return pd.DataFrame(
        [
            {
                "check": "indicator_columns",
                "status": "ok" if not missing_columns else "error",
                "detail": "缺失列: " + "、".join(missing_columns) if missing_columns else "指标列完整",
            },
            {
                "check": "extra_columns",
                "status": "ok" if not extra_columns else "info",
                "detail": "、".join(extra_columns),
            },
        ]
    )


def quality_report(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "province_coverage": province_coverage_report(df),
        "indicator_columns": indicator_column_report(df),
        "missing_values": missing_value_report(df),
    }


def check_cached_indicators(year: int = 2024) -> dict[str, pd.DataFrame]:
    df = get_indicators(year)
    return quality_report(df)
