"""ranking.py — TOP10 综合得分排名榜

接口对齐 analyzer.analyze() 返回的 ``scores`` DataFrame：
    列：['province', 'score', 'rank']   rank 已由模型层计算
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.transforms import blended_transform_factory

from ._style import (
    RANK_BRONZE,
    RANK_GOLD,
    RANK_NORMAL,
    RANK_SILVER,
    ensure_output_dir,
    setup_chinese_font,
)


def draw_ranking(
    scores: pd.DataFrame,
    *,
    top_n: int = 10,
    output_dir: os.PathLike | str | None = None,
    year: Optional[int] = None,
    show_bottom: bool = True,
) -> dict:
    """绘制 TOP N 排名榜（水平柱状图）。

    Parameters
    ----------
    scores : DataFrame
        必含 ``province`` 和 ``score`` 两列。若有 ``rank`` 列将直接使用，
        否则按 score 降序自动生成。
    top_n : int  默认 10
    show_bottom : bool  是否生成末尾 5 名副图

    Returns
    -------
    dict  {"top_png": Path, "bottom_png": Path|None, "full_png": Path}
    """
    setup_chinese_font()
    out_dir = ensure_output_dir(output_dir)
    suffix = f"_{year}" if year else ""

    for col in ("province", "score"):
        if col not in scores.columns:
            raise ValueError(f"scores 缺少列 '{col}'，实际列: {list(scores.columns)}")

    df = scores[["province", "score"]].dropna().copy()
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    # ---- TOP N ----
    top_df = df.head(top_n)
    top_png = _plot_horizontal_ranking(
        top_df,
        title=f"省域经济综合竞争力 TOP {top_n}{('  ' + str(year) + '年') if year else ''}",
        save_path=out_dir / f"05_排名榜_TOP{top_n}{suffix}.png",
        highlight_top3=True,
    )

    # ---- 末尾 5 名 ----
    bottom_png = None
    if show_bottom and len(df) > top_n + 5:
        bottom_df = df.tail(5).sort_values("score", ascending=True).reset_index(drop=True)
        bottom_png = _plot_horizontal_ranking(
            bottom_df,
            title=f"末尾 5 名 — 待振兴地区{('  ' + str(year) + '年') if year else ''}",
            save_path=out_dir / f"06_排名榜_末尾5{suffix}.png",
            highlight_top3=False,
            color_override="#7a7a7a",
        )

    # ---- 完整 31 省 ----
    full_png = _plot_horizontal_ranking(
        df,
        title=f"31 省综合竞争力完整排名{('  ' + str(year) + '年') if year else ''}",
        save_path=out_dir / f"07_排名榜_完整{suffix}.png",
        highlight_top3=True,
        compact=True,
    )

    return {"top_png": top_png, "bottom_png": bottom_png, "full_png": full_png}


def _plot_horizontal_ranking(
    df: pd.DataFrame,
    *,
    title: str,
    save_path: Path,
    highlight_top3: bool = True,
    color_override: Optional[str] = None,
    compact: bool = False,
) -> Path:
    n = len(df)
    fig_height = max(7, 0.32 * n + 1.5) if compact else max(4.5, 0.45 * n + 1.5)
    fig, ax = plt.subplots(figsize=(11, fig_height))

    df_plot = df.iloc[::-1].reset_index(drop=True)
    n = len(df_plot)

    if color_override:
        colors = [color_override] * n
    elif highlight_top3:
        colors = []
        for i in range(n):
            rank = n - i
            if rank == 1:
                colors.append(RANK_GOLD)
            elif rank == 2:
                colors.append(RANK_SILVER)
            elif rank == 3:
                colors.append(RANK_BRONZE)
            else:
                colors.append(RANK_NORMAL)
    else:
        colors = [RANK_NORMAL] * n

    bars = ax.barh(
        df_plot["province"],
        df_plot["score"],
        color=colors,
        edgecolor="white",
        linewidth=0.6,
    )

    max_score = df_plot["score"].max()
    for bar, score in zip(bars, df_plot["score"]):
        ax.text(
            bar.get_width() + max_score * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{score:.2f}",
            ha="left",
            va="center",
            fontsize=9 if compact else 10,
            color="#333",
        )

    if highlight_top3:
        medals = {n - 1: ("①", RANK_GOLD), n - 2: ("②", RANK_SILVER), n - 3: ("③", RANK_BRONZE)}
        trans = blended_transform_factory(ax.transAxes, ax.transData)
        for idx, (mark, mc) in medals.items():
            if 0 <= idx < n:
                ax.text(
                    -0.085 if not compact else -0.06,
                    idx,
                    mark,
                    ha="center",
                    va="center",
                    fontsize=18 if compact else 22,
                    weight="bold",
                    color=mc,
                    transform=trans,
                    clip_on=False,
                )

    ax.set_xlabel("综合得分", fontsize=12)
    ax.set_xlim(0, max_score * 1.13)
    ax.set_title(title, fontsize=15, weight="bold", pad=15)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(axis="y", length=0, labelsize=10 if compact else 11)
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"[ranking] PNG 已生成: {save_path}")
    return save_path
