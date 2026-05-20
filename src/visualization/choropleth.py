"""choropleth.py — 中国省域综合得分热力图（Matplotlib 静态渲染）

This module renders stable static PNG maps from GeoJSON polygons and wraps
those images in standalone HTML files. It intentionally avoids browser-side
Plotly choropleth rendering because that path can differ across platforms
(e.g. WebGL / binary bdata decoding issues on Linux).
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

from ._style import (
    SCORE_COLORSCALE,
    TIER_COLOR_BY_LABEL,
    TIER_NAMES_BY_LABEL,
    ensure_output_dir,
    normalize_province_name,
    setup_chinese_font,
)


# ---------------------------------------------------------------------------
# GeoJSON 缓存
# ---------------------------------------------------------------------------

GEOJSON_URLS = [
    "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
    "https://raw.githubusercontent.com/Plortinus/china-geojson/master/china.json",
]
GEOJSON_CACHE = Path("data_cache") / "china_provinces.geojson"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _load_china_geojson() -> dict:
    GEOJSON_CACHE.parent.mkdir(parents=True, exist_ok=True)

    if GEOJSON_CACHE.exists():
        with open(GEOJSON_CACHE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _clean_geojson(data)

    print("[choropleth] 首次运行，正在下载中国省级 GeoJSON ...")
    last_err: Optional[Exception] = None
    for url in GEOJSON_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            data = _clean_geojson(data)
            with open(GEOJSON_CACHE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"[choropleth] 已缓存到 {GEOJSON_CACHE}  (来源: {url})")
            return data
        except Exception as e:
            print(f"[choropleth] 下载失败 ({url}): {e}")
            last_err = e

    raise RuntimeError(
        f"GeoJSON 下载失败。请手动下载 {GEOJSON_URLS[0]} 到 {GEOJSON_CACHE}\n"
        f"最后一次错误: {last_err}"
    )


def _clean_geojson(geojson: dict) -> dict:
    features = []
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        name = properties.get("name", "")
        if isinstance(name, str) and name.strip():
            features.append(feature)

    cleaned = dict(geojson)
    cleaned["features"] = features
    return cleaned


# ---------------------------------------------------------------------------
# Colormap
# ---------------------------------------------------------------------------


def _score_colormap() -> mcolors.LinearSegmentedColormap:
    colors = [(pos, color) for pos, color in SCORE_COLORSCALE]
    return mcolors.LinearSegmentedColormap.from_list("province_score", colors)


# ---------------------------------------------------------------------------
# GeoJSON → Polygon helpers
# ---------------------------------------------------------------------------


def _iter_polygons(geometry: dict):
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geom_type == "Polygon":
        for ring in coordinates[:1]:
            yield ring
    elif geom_type == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon[:1]:
                yield ring


def _polygon_patch(ring: list) -> Polygon | None:
    if len(ring) < 3:
        return None

    points = []
    for point in ring:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        points.append((float(point[0]), float(point[1])))

    if len(points) < 3:
        return None
    return Polygon(points, closed=True)


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------


def _build_score_frame(scores: pd.DataFrame) -> pd.DataFrame:
    for col in ("province", "score"):
        if col not in scores.columns:
            raise ValueError(f"scores 缺少列 '{col}'，实际列: {list(scores.columns)}")

    df = scores[["province", "score"]].copy()
    df["province"] = df["province"].map(normalize_province_name)
    df["score"] = pd.to_numeric(df["score"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["province", "score"])
    dropped = before - len(df)
    if dropped:
        print(f"[choropleth] 警告: {dropped} 个省份因名称或得分缺失被跳过")

    return df


def _build_tier_frame(clusters: pd.DataFrame) -> pd.DataFrame:
    for col in ("province", "label"):
        if col not in clusters.columns:
            raise ValueError(f"clusters 缺少列 '{col}'，实际列: {list(clusters.columns)}")

    df = clusters[["province", "label"]].copy()
    df["province"] = df["province"].map(normalize_province_name)
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    df = df.dropna(subset=["province", "label"])
    df["label"] = df["label"].astype(int)
    df["梯队"] = df["label"].map(TIER_NAMES_BY_LABEL)
    return df


# ---------------------------------------------------------------------------
# Map rendering
# ---------------------------------------------------------------------------


def _collect_feature_patches(geojson: dict):
    patches_by_name: dict[str, list[Polygon]] = {}
    all_patches: list[Polygon] = []

    for feature in geojson.get("features", []):
        name = feature.get("properties", {}).get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        province_patches = []
        for ring in _iter_polygons(feature.get("geometry", {})):
            patch = _polygon_patch(ring)
            if patch is not None:
                province_patches.append(patch)
                all_patches.append(patch)

        if province_patches:
            patches_by_name[name] = province_patches

    return patches_by_name, all_patches


def _set_map_bounds(ax, patches: list[Polygon]) -> None:
    xs = []
    ys = []
    for patch in patches:
        vertices = patch.get_xy()
        xs.extend(vertices[:, 0])
        ys.extend(vertices[:, 1])

    if not xs or not ys:
        return

    x_margin = (max(xs) - min(xs)) * 0.03
    y_margin = (max(ys) - min(ys)) * 0.03
    ax.set_xlim(min(xs) - x_margin, max(xs) + x_margin)
    ax.set_ylim(min(ys) - y_margin, max(ys) + y_margin)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")


def _save_html_from_png(png_path: Path, html_path: Path, title: str) -> None:
    with open(png_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      background: #ffffff;
      font-family: "Noto Sans CJK SC", "Source Han Sans CN", "Microsoft YaHei", sans-serif;
    }}
    .wrap {{
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      box-sizing: border-box;
    }}
    img {{
      max-width: 100%;
      max-height: calc(100vh - 48px);
      object-fit: contain;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <img alt="{title}" src="data:image/png;base64,{encoded}">
  </div>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")


def _draw_score_map(
    geojson: dict,
    scores: pd.DataFrame,
    png_path: Path,
    html_path: Path,
    title: str,
) -> None:
    setup_chinese_font()

    score_by_province = dict(zip(scores["province"], scores["score"]))
    patches_by_name, all_patches = _collect_feature_patches(geojson)

    fig, ax = plt.subplots(figsize=(14, 9))
    cmap = _score_colormap()
    norm = mcolors.Normalize(vmin=0, vmax=100)

    matched = 0
    for province, patches in patches_by_name.items():
        score = score_by_province.get(province)
        if score is None:
            facecolor = "#f2f2f2"
        else:
            matched += 1
            facecolor = cmap(norm(float(score)))

        collection = PatchCollection(
            patches,
            facecolor=facecolor,
            edgecolor="#ffffff",
            linewidth=0.6,
            antialiased=True,
        )
        ax.add_collection(collection)

    _set_map_bounds(ax, all_patches)
    ax.set_title(title, fontsize=20, pad=18)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.028, pad=0.02)
    cbar.set_label("得分", fontsize=12)
    cbar.ax.tick_params(labelsize=10)

    fig.tight_layout()
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    _save_html_from_png(png_path, html_path, title)
    print(f"[choropleth] 匹配省份: {matched}/{len(scores)}")
    print(f"[choropleth] PNG 已生成: {png_path}")
    print(f"[choropleth] HTML 已生成: {html_path}")


def _draw_tier_map(
    geojson: dict,
    clusters: pd.DataFrame,
    png_path: Path,
    html_path: Path,
    title: str,
) -> None:
    setup_chinese_font()

    label_by_province = dict(zip(clusters["province"], clusters["label"]))
    patches_by_name, all_patches = _collect_feature_patches(geojson)

    fig, ax = plt.subplots(figsize=(14, 9))

    matched = 0
    for province, patches in patches_by_name.items():
        label = label_by_province.get(province)
        if label is None:
            facecolor = "#f2f2f2"
        else:
            matched += 1
            facecolor = TIER_COLOR_BY_LABEL.get(int(label), "#cccccc")

        collection = PatchCollection(
            patches,
            facecolor=facecolor,
            edgecolor="#ffffff",
            linewidth=0.6,
            antialiased=True,
        )
        ax.add_collection(collection)

    _set_map_bounds(ax, all_patches)
    ax.set_title(title, fontsize=20, pad=18)

    labels = sorted(clusters["label"].unique())
    legend_handles = [
        Polygon(
            [(0, 0), (1, 0), (1, 1)],
            facecolor=TIER_COLOR_BY_LABEL[int(label)],
            edgecolor="none",
            label=TIER_NAMES_BY_LABEL[int(label)],
        )
        for label in labels
        if int(label) in TIER_COLOR_BY_LABEL and int(label) in TIER_NAMES_BY_LABEL
    ]
    ax.legend(
        handles=legend_handles,
        title="梯队",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
    )

    fig.tight_layout()
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    _save_html_from_png(png_path, html_path, title)
    print(f"[choropleth] 梯队匹配省份: {matched}/{len(clusters)}")
    print(f"[choropleth] 梯队 PNG 已生成: {png_path}")
    print(f"[choropleth] 梯队 HTML 已生成: {html_path}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def draw_map(
    scores: pd.DataFrame,
    clusters: Optional[pd.DataFrame] = None,
    *,
    output_dir: os.PathLike | str | None = None,
    year: Optional[int] = None,
    save_png: bool = True,
) -> dict:
    """Render China province score heatmap + optional tier cluster map.

    Parameters
    ----------
    scores : DataFrame
        Must contain ``province`` and ``score`` columns.
    clusters : DataFrame, optional
        Must contain ``province`` and ``label`` columns.
    year : int, optional
        Appended to title and filenames.
    output_dir : path, optional
        Output directory (default: ``output/``).

    Returns
    -------
    dict  {"html": Path, "png": Path|None, "tier_html": Path|None, "tier_png": Path|None}
    """
    out_dir = ensure_output_dir(output_dir)
    suffix = f"_{year}" if year else ""

    geojson = _load_china_geojson()
    score_df = _build_score_frame(scores)

    score_title = (
        f"中国省域经济综合竞争力 - 综合得分热力图"
        f"{(' ' + str(year) + '年') if year else ''}"
    )
    html_path = out_dir / f"01_中国地图_综合得分热力图{suffix}.html"
    png_path = out_dir / f"01_中国地图_综合得分热力图{suffix}.png"

    _draw_score_map(geojson, score_df, png_path, html_path, score_title)

    result = {
        "html": html_path,
        "png": png_path if save_png else None,
        "tier_html": None,
        "tier_png": None,
    }

    if not save_png and png_path.exists():
        png_path.unlink()

    # ---- 副图：聚类梯队 ----
    if clusters is not None:
        tier_df = _build_tier_frame(clusters)
        tier_title = (
            f"中国省域经济竞争力 - 四梯队聚类分布"
            f"{(' ' + str(year) + '年') if year else ''}"
        )
        tier_html = out_dir / f"02_中国地图_聚类梯队分布{suffix}.html"
        tier_png = out_dir / f"02_中国地图_聚类梯队分布{suffix}.png"

        _draw_tier_map(geojson, tier_df, tier_png, tier_html, tier_title)

        result["tier_html"] = tier_html
        result["tier_png"] = tier_png if save_png else None

        if not save_png and tier_png.exists():
            tier_png.unlink()

    return result
