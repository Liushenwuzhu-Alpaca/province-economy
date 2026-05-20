"""data_api.py — JSON data export layer for ECharts dashboard frontend.

Reads cached results and exports structured JSON for the frontend.
Designed to be server-independent; main.py imports from here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.visualization._style import INDICATOR_LABELS_CN, TIER_NAMES_BY_LABEL
from src.visualization.radar import (
    ANALYSIS_INDICATORS,
    NEGATIVE_INDICATORS,
    _preprocess_indicators,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_RESULTS = Path("data/results")
_DATA_CACHE = Path("data_cache")
_GEOJSON_CACHE = _DATA_CACHE / "china_provinces.geojson"


# ---------------------------------------------------------------------------
# Helper: ensure JSON-serializable
# ---------------------------------------------------------------------------


def _to_native(obj: Any) -> Any:
    """Recursively convert numpy/Python special types to plain JSON-native types."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# load_scores_json
# ---------------------------------------------------------------------------


def load_scores_json(year: int = 2024) -> dict:
    """Load PCA composite scores as JSON-serializable dict.

    Returns
    -------
    dict  {"provinces": [...], "scores": [...], "ranks": [...]}
    """
    path = _DATA_RESULTS / f"{year}_pca" / "scores.csv"
    df = pd.read_csv(path)

    return _to_native(
        {
            "provinces": df["province"].tolist(),
            "scores": df["score"].tolist(),
            "ranks": df["rank"].tolist(),
        }
    )


# ---------------------------------------------------------------------------
# load_clusters_json
# ---------------------------------------------------------------------------


def load_clusters_json(year: int = 2024) -> dict:
    """Load K-Means cluster labels with tier names.

    Returns
    -------
    dict  {"provinces": [...], "labels": [...], "tier_names": [...]}
    """
    path = _DATA_RESULTS / f"{year}_pca" / "clusters.csv"
    df = pd.read_csv(path)

    labels = df["label"].astype(int).tolist()
    tier_names = [TIER_NAMES_BY_LABEL.get(int(l), f"梯队{l}") for l in labels]

    return _to_native(
        {
            "provinces": df["province"].tolist(),
            "labels": labels,
            "tier_names": tier_names,
        }
    )


# ---------------------------------------------------------------------------
# load_radar_data
# ---------------------------------------------------------------------------


def load_radar_data(year: int = 2024) -> dict:
    """Load normalized radar indicator data for all 31 provinces.

    Applies the same CPI transform (|CPI-100|), negative reverse, and
    MinMax normalization as radar.py.

    Returns
    -------
    dict  {"provinces": [...], "indicators": [...], "values": [[...], ...]}
    """
    raw_path = _DATA_CACHE / f"indicators_{year}.csv"
    raw_df = pd.read_csv(raw_path, index_col="province")
    raw_df = raw_df.reset_index()

    indicator_cols = [c for c in ANALYSIS_INDICATORS if c in raw_df.columns]
    normed = _preprocess_indicators(raw_df, indicator_cols)

    provinces = raw_df["province"].tolist()
    indicators = [INDICATOR_LABELS_CN.get(c, c) for c in indicator_cols]
    values = normed[indicator_cols].values.tolist()

    return _to_native(
        {
            "provinces": provinces,
            "indicators": indicators,
            "values": values,
        }
    )


# ---------------------------------------------------------------------------
# load_ranking_json
# ---------------------------------------------------------------------------


def load_ranking_json(year: int = 2024) -> dict:
    """Load full ranking list (province + score + rank) as JSON.

    Returns
    -------
    dict  {"rankings": [{"province": ..., "score": ..., "rank": ...}, ...]}
    """
    path = _DATA_RESULTS / f"{year}_pca" / "scores.csv"
    df = pd.read_csv(path)

    rankings = [
        {"province": row["province"], "score": row["score"], "rank": row["rank"]}
        for _, row in df.iterrows()
    ]

    return _to_native({"rankings": rankings})


# ---------------------------------------------------------------------------
# load_geojson
# ---------------------------------------------------------------------------


def load_geojson() -> dict:
    """Load and clean China provinces GeoJSON.

    Removes features with empty/null names to avoid rendering issues.

    Returns
    -------
    dict  GeoJSON FeatureCollection
    """
    if not _GEOJSON_CACHE.exists():
        raise FileNotFoundError(
            f"GeoJSON cache not found at {_GEOJSON_CACHE}. "
            "Run choropleth.py or fetch from DataV/GeoGitHub first."
        )

    with open(_GEOJSON_CACHE, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    cleaned_features = []
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        name = props.get("name", "")
        if isinstance(name, str) and name.strip():
            cleaned_features.append(feature)

    cleaned = dict(geojson)
    cleaned["features"] = cleaned_features
    return cleaned


# ---------------------------------------------------------------------------
# load_all_data
# ---------------------------------------------------------------------------


def load_all_data(year: int = 2024) -> dict:
    """Aggregate all dashboard data into a single JSON-serializable dict.

    Parameters
    ----------
    year : int
        Analysis year for scores, clusters, and radar data.

    Returns
    -------
    dict  {
        "scores": load_scores_json(),
        "clusters": load_clusters_json(),
        "radar": load_radar_data(),
        "ranking": load_ranking_json(),
        "geojson": load_geojson(),
    }
    """
    return _to_native(
        {
            "scores": load_scores_json(year),
            "clusters": load_clusters_json(year),
            "radar": load_radar_data(year),
            "ranking": load_ranking_json(year),
            "geojson": load_geojson(),
        }
    )


# ---------------------------------------------------------------------------
# load_trend_data
# ---------------------------------------------------------------------------


def load_trend_data() -> dict:
    """Aggregate scores across all available years for trend chart.

    Returns
    -------
    dict  {
        "years": [2019, 2020, ...],
        "provinces": ["广东", "江苏", ...],  # 31 provinces
        "series": [
            {"province": "广东", "year": 2019, "score": 85.5},
            {"province": "广东", "year": 2020, "score": 88.2},
            ...
        ]
    }
    """
    years = []
    if _DATA_RESULTS.exists():
        for entry in _DATA_RESULTS.iterdir():
            if entry.is_dir():
                m = re.match(r"^(\d{4})_pca$", entry.name)
                if m:
                    scores_file = entry / "scores.csv"
                    if scores_file.exists():
                        years.append(int(m.group(1)))
    years.sort()

    all_series = []
    province_set = set()

    for year in years:
        df = pd.read_csv(_DATA_RESULTS / f"{year}_pca" / "scores.csv")
        for _, row in df.iterrows():
            all_series.append(
                {
                    "province": row["province"],
                    "year": year,
                    "score": round(float(row["score"]), 2),
                }
            )
            province_set.add(row["province"])

    return _to_native(
        {
            "years": years,
            "provinces": sorted(province_set),
            "series": all_series,
        }
    )
