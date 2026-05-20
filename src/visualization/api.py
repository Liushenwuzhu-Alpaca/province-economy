"""api.py — 可视化高层入口

main.py 一行调用：
    from src.visualization import render_all
    render_all(result, raw_df, year=2024)

会自动调用四个绘图函数，生成所有 PNG + HTML 到 ``output/`` 目录。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd

from .choropleth import draw_map
from .radar import draw_radar
from .ranking import draw_ranking
from .trend import draw_trend


def render_year(
    result: dict,
    raw_df: pd.DataFrame,
    year: int,
    *,
    output_dir: os.PathLike | str | None = None,
) -> dict:
    """单年份的可视化。

    Parameters
    ----------
    result : dict
        analyzer.analyze() 的返回值。需含 'scores' 和 'clusters'。
    raw_df : DataFrame
        get_indicators(year) 的原始返回（雷达图要用原始值做归一化）。
    year : int
        年份。
    """
    outputs = {}

    print(f"\n[可视化] 开始渲染 {year} 年图表 → output/")

    # 1. 中国地图（热力图 + 梯队）
    outputs.update(
        draw_map(result["scores"], result["clusters"],
                 year=year, output_dir=output_dir)
    )

    # 2. 雷达图（典型省份 + 案例对比）
    outputs.update(
        draw_radar(raw_df, year=year, output_dir=output_dir)
    )

    # 3. 排名榜
    outputs.update(
        draw_ranking(result["scores"], year=year, output_dir=output_dir)
    )

    print(f"[可视化] {year} 年图表完成。")
    return outputs


def render_all(
    yearly_results: dict[int, dict],
    yearly_raw_df: dict[int, pd.DataFrame],
    *,
    output_dir: os.PathLike | str | None = None,
) -> dict:
    """多年份的可视化（含趋势图）。

    Parameters
    ----------
    yearly_results : dict[int, dict]
        年份 → analyze() 返回值。
    yearly_raw_df : dict[int, DataFrame]
        年份 → get_indicators() 返回值。
    """
    outputs = {}
    years = sorted(yearly_results.keys())
    latest = years[-1]

    # 单年图表只用最新年份的数据
    outputs.update(
        render_year(yearly_results[latest], yearly_raw_df[latest],
                    latest, output_dir=output_dir)
    )

    # 趋势图汇总各年得分
    if len(years) >= 2:
        rows = []
        for y in years:
            scores = yearly_results[y]["scores"]
            for _, row in scores.iterrows():
                rows.append({
                    "province": row["province"],
                    "year": y,
                    "score": row["score"],
                })
        trend_long = pd.DataFrame(rows)
        outputs.update(draw_trend(trend_long, output_dir=output_dir))
    else:
        print(f"[可视化] 仅 {len(years)} 年的数据，跳过趋势图。")

    print("\n" + "=" * 60)
    print("  所有图表已生成 → output/")
    print("=" * 60)

    return outputs
