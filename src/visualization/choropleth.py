"""choropleth.py — 中国省域综合得分热力图（Plotly）

接口对齐 ``src.models.analyzer.analyze()`` 的返回：
  - scores:   DataFrame [province, score, rank]
  - clusters: DataFrame [province, label]   label ∈ {0,1,2,3}

输出：HTML（交互式）+ PNG（PPT 用）。
HTML 文件**自带 plotlyjs**（include_plotlyjs=True），可离线打开。
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px

from ._style import (
    SCORE_COLORSCALE,
    TIER_COLOR_BY_LABEL,
    TIER_NAMES_BY_LABEL,
    ensure_output_dir,
    normalize_province_name,
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
            return json.load(f)

    print("[choropleth] 首次运行，正在下载中国省级 GeoJSON ...")
    last_err: Optional[Exception] = None
    for url in GEOJSON_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _BROWSER_UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
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


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def draw_map(
    scores: pd.DataFrame,
    clusters: Optional[pd.DataFrame] = None,
    *,
    output_dir: os.PathLike | str | None = None,
    year: Optional[int] = None,
    save_png: bool = True,
) -> dict:
    """绘制中国省域综合得分热力地图 + 聚类梯队副图。

    Parameters
    ----------
    scores : DataFrame  必含 ``province`` 和 ``score`` 两列
        即 analyzer.analyze() 返回的 result['scores']
    clusters : DataFrame, optional  含 ``province`` 和 ``label`` 两列
        即 analyzer.analyze() 返回的 result['clusters']
    year : int, optional  拼入标题与文件名

    Returns
    -------
    dict  {"html": Path, "png": Path|None, "tier_html": Path|None, "tier_png": Path|None}
    """
    out_dir = ensure_output_dir(output_dir)
    suffix = f"_{year}" if year else ""

    # ---- 数据校验 ----
    for col in ("province", "score"):
        if col not in scores.columns:
            raise ValueError(f"scores 缺少列 '{col}'，实际列: {list(scores.columns)}")

    df = scores.copy()
    df["province"] = df["province"].map(normalize_province_name)

    geojson = _load_china_geojson()

    # ---- 主图：得分热力图 ----
    title = f"中国省域经济综合竞争力 — 综合得分热力图{(' ' + str(year) + '年') if year else ''}"

    fig = px.choropleth(
        df,
        geojson=geojson,
        featureidkey="properties.name",
        locations="province",
        color="score",
        color_continuous_scale=SCORE_COLORSCALE,
        range_color=(0, 100),
        labels={"score": "综合得分"},
        hover_name="province",
        hover_data={"score": ":.2f", "province": False},
    )
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=20)),
        margin=dict(l=0, r=0, t=60, b=0),
        coloraxis_colorbar=dict(title="得分", ticksuffix=" 分", len=0.7, thickness=18),
        font=dict(family="Microsoft YaHei, SimHei, PingFang SC, sans-serif"),
    )

    html_path = out_dir / f"01_中国地图_综合得分热力图{suffix}.html"
    # include_plotlyjs=True → 离线可打开（不依赖 CDN）
    fig.write_html(str(html_path), include_plotlyjs=True)
    print(f"[choropleth] HTML 已生成: {html_path}")

    png_path = None
    if save_png:
        png_path = out_dir / f"01_中国地图_综合得分热力图{suffix}.png"
        try:
            fig.write_image(str(png_path), width=1400, height=900, scale=2)
            print(f"[choropleth] PNG 已生成: {png_path}")
        except Exception as e:
            print(f"[choropleth] PNG 导出失败（HTML 已生成）: {e}")
            print("           若需 PNG，请运行: pip install -U kaleido")
            png_path = None

    result = {"html": html_path, "png": png_path, "tier_html": None, "tier_png": None}

    # ---- 副图：聚类梯队 ----
    if clusters is not None:
        for col in ("province", "label"):
            if col not in clusters.columns:
                raise ValueError(
                    f"clusters 缺少列 '{col}'，实际列: {list(clusters.columns)}"
                )

        tier_df = clusters.copy()
        tier_df["province"] = tier_df["province"].map(normalize_province_name)
        tier_df["梯队"] = tier_df["label"].map(TIER_NAMES_BY_LABEL)

        # 保持图例顺序
        present_order = [TIER_NAMES_BY_LABEL[i]
                         for i in sorted(tier_df["label"].unique())
                         if i in TIER_NAMES_BY_LABEL]
        color_map = {TIER_NAMES_BY_LABEL[i]: TIER_COLOR_BY_LABEL[i]
                     for i in sorted(tier_df["label"].unique())
                     if i in TIER_NAMES_BY_LABEL}

        fig2 = px.choropleth(
            tier_df,
            geojson=geojson,
            featureidkey="properties.name",
            locations="province",
            color="梯队",
            category_orders={"梯队": present_order},
            color_discrete_map=color_map,
            hover_name="province",
        )
        fig2.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
        fig2.update_layout(
            title=dict(
                text=f"中国省域经济竞争力 — 四梯队聚类分布{(' ' + str(year) + '年') if year else ''}",
                x=0.5, xanchor="center", font=dict(size=20),
            ),
            margin=dict(l=0, r=0, t=60, b=0),
            legend=dict(title="梯队", orientation="v", x=1.0, y=0.5),
            font=dict(family="Microsoft YaHei, SimHei, PingFang SC, sans-serif"),
        )

        tier_html = out_dir / f"02_中国地图_聚类梯队分布{suffix}.html"
        fig2.write_html(str(tier_html), include_plotlyjs=True)
        result["tier_html"] = tier_html
        print(f"[choropleth] 梯队 HTML 已生成: {tier_html}")

        if save_png:
            tier_png = out_dir / f"02_中国地图_聚类梯队分布{suffix}.png"
            try:
                fig2.write_image(str(tier_png), width=1400, height=900, scale=2)
                result["tier_png"] = tier_png
                print(f"[choropleth] 梯队 PNG 已生成: {tier_png}")
            except Exception:
                pass

    return result
