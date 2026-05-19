"""trend.py — 多年份得分趋势折线图

接口：长表 DataFrame，列 [province, year, score]
（由 api.render_all() 在调用方循环各年汇总产出）

若只有一个年份的数据，自动跳过趋势绘制（main.py 当前只跑单年时不会报错）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence

import matplotlib.pyplot as plt
import pandas as pd

from ._style import (
    PROVINCE_PALETTE,
    ensure_output_dir,
    setup_chinese_font,
)


def draw_trend(
    data: pd.DataFrame,
    provinces: Optional[Sequence[str]] = None,
    *,
    output_dir: os.PathLike | str | None = None,
    show_top_n: int = 5,
    show_bottom_n: int = 3,
) -> dict:
    """绘制多省份多年度得分趋势。

    Parameters
    ----------
    data : DataFrame  长表，列 [province, year, score]
    provinces : list[str], optional  指定省份；默认 TOP N + BOTTOM M
    """
    setup_chinese_font()
    out_dir = ensure_output_dir(output_dir)

    for col in ("province", "year", "score"):
        if col not in data.columns:
            raise ValueError(f"data 缺少列 '{col}'，实际列: {list(data.columns)}")

    df = data[["province", "year", "score"]].copy()
    df["year"] = df["year"].astype(int)
    df = df.sort_values(["province", "year"])

    years = sorted(df["year"].unique())
    if len(years) < 2:
        print(f"[trend] 仅 {len(years)} 个年份的数据，跳过趋势图（至少需 2 年）。")
        return {"top_png": None, "compare_png": None}

    latest_year = years[-1]

    if provinces is None:
        latest = df[df["year"] == latest_year].sort_values("score", ascending=False)
        top_provinces = latest.head(show_top_n)["province"].tolist()
        bottom_provinces = latest.tail(show_bottom_n)["province"].tolist()
        provinces = top_provinces + bottom_provinces
    else:
        provinces = list(provinces)

    main_png = _plot_trend(
        df, provinces,
        title=f"省域经济综合得分多年趋势（{years[0]}—{years[-1]}）",
        save_path=out_dir / "08_趋势图_多省份对比.png",
    )

    compare_png = _plot_region_compare(
        df, save_path=out_dir / "09_趋势图_东中西部对比.png",
    )

    return {"top_png": main_png, "compare_png": compare_png}


def _plot_trend(df, provinces, *, title, save_path):
    fig, ax = plt.subplots(figsize=(12, 6.5))

    for i, province in enumerate(provinces):
        sub = df[df["province"] == province].sort_values("year")
        if sub.empty:
            print(f"[trend] 警告：{province} 无数据，已跳过")
            continue
        color = PROVINCE_PALETTE[i % len(PROVINCE_PALETTE)]
        ax.plot(
            sub["year"], sub["score"],
            marker="o", linewidth=2.2, markersize=7,
            label=province, color=color,
        )
        ax.text(
            sub["year"].iloc[-1] + 0.05,
            sub["score"].iloc[-1],
            f" {sub['score'].iloc[-1]:.1f}",
            color=color, fontsize=9, va="center", weight="bold",
        )

    ax.set_xlabel("年份", fontsize=12)
    ax.set_ylabel("综合得分", fontsize=12)
    ax.set_title(title, fontsize=15, weight="bold", pad=15)
    ax.grid(alpha=0.35, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=11, frameon=False)

    years = sorted(df["year"].unique())
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years])

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"[trend] PNG 已生成: {save_path}")
    return save_path


# 东、中、西部经济区划（国家统计局口径）
EAST = {"北京市", "天津市", "河北省", "辽宁省", "上海市", "江苏省",
        "浙江省", "福建省", "山东省", "广东省", "海南省"}
CENTRAL = {"山西省", "吉林省", "黑龙江省", "安徽省", "江西省",
           "河南省", "湖北省", "湖南省"}
WEST = {"内蒙古自治区", "广西壮族自治区", "重庆市", "四川省", "贵州省",
        "云南省", "西藏自治区", "陕西省", "甘肃省", "青海省",
        "宁夏回族自治区", "新疆维吾尔自治区"}


def _classify_region(province):
    if province in EAST: return "东部"
    if province in CENTRAL: return "中部"
    if province in WEST: return "西部"
    return "其他"


def _plot_region_compare(df, *, save_path):
    df = df.copy()
    df["region"] = df["province"].map(_classify_region)
    df = df[df["region"] != "其他"]
    if df.empty:
        return None

    grouped = df.groupby(["region", "year"])["score"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(11, 6))
    region_colors = {"东部": "#b8311a", "中部": "#e89c5f", "西部": "#4a7ab8"}
    for region in ["东部", "中部", "西部"]:
        sub = grouped[grouped["region"] == region].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub["year"], sub["score"], marker="o",
                linewidth=2.6, markersize=9,
                label=region, color=region_colors[region])
        ax.fill_between(sub["year"], sub["score"],
                        alpha=0.08, color=region_colors[region])

    ax.set_xlabel("年份", fontsize=12)
    ax.set_ylabel("区域平均综合得分", fontsize=12)
    ax.set_title("东中西部经济综合竞争力区域均值趋势对比",
                 fontsize=15, weight="bold", pad=15)
    ax.grid(alpha=0.35, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="best", fontsize=12, frameon=True, framealpha=0.9)

    years = sorted(grouped["year"].unique())
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years])

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"[trend] PNG 已生成: {save_path}")
    return save_path
