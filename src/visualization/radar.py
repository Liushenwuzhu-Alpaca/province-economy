"""radar.py — 省份多维雷达图

接口对齐 analyzer.analyze() 的输入：raw_df 是 get_indicators(year) 返回的
原始指标 DataFrame（31 省 × 10 指标 + province 列）。

本模块内部会复刻 analyzer 中的处理：
  - CPI 转为 |CPI - 100|（偏离 100 越远越不利）
  - 负向指标反向（unemployment / cpi → 越小越好）
  - Min-Max 归一化到 [0,1]

这样雷达图上所有指标都是「正向越大越好」，便于直观对比。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ._style import (
    PROVINCE_PALETTE,
    ensure_output_dir,
    label_of,
    setup_chinese_font,
)


# 与 analyzer.DIRECTIONS 严格一致
NEGATIVE_INDICATORS = {"cpi", "unemployment"}


def _preprocess_indicators(
    raw_df: pd.DataFrame,
    indicator_cols: Sequence[str],
) -> pd.DataFrame:
    """复刻 analyzer 的预处理（CPI 偏离 + 反向 + Min-Max）。"""
    df = raw_df[list(indicator_cols)].copy().astype(float)

    # CPI 转为偏离 100 的绝对值
    if "cpi" in df.columns:
        df["cpi"] = (df["cpi"] - 100.0).abs()

    # 负向指标反向（max - x），让所有列都变成「越大越好」
    for col in df.columns:
        if col in NEGATIVE_INDICATORS:
            col_max = df[col].max()
            df[col] = col_max - df[col]

    # Min-Max 归一化到 [0, 1]
    for col in df.columns:
        lo, hi = df[col].min(), df[col].max()
        if hi - lo < 1e-10:
            df[col] = 0.5
        else:
            df[col] = (df[col] - lo) / (hi - lo)

    return df


def draw_radar(
    raw_df: pd.DataFrame,
    provinces: Optional[Sequence[str]] = None,
    *,
    indicator_cols: Optional[Sequence[str]] = None,
    output_dir: os.PathLike | str | None = None,
    year: Optional[int] = None,
    case_pair: Optional[tuple[str, str]] = ("江苏省", "贵州省"),
) -> dict:
    """绘制省份雷达对比图。

    Parameters
    ----------
    raw_df : DataFrame
        get_indicators(year) 的原始返回值。必含 'province' 列 + 各指标列。
    provinces : list[str], optional
        要展示的省份。默认 京沪粤苏浙 5 省。
    indicator_cols : list[str], optional
        指标列。默认用 raw_df 中所有非 'province' 列。
    case_pair : tuple, optional
        额外生成"案例对比"图（PPT 第 7 页）。传 None 关闭。

    Returns
    -------
    dict  {"main_png": Path, "case_png": Path|None}
    """
    setup_chinese_font()
    out_dir = ensure_output_dir(output_dir)
    suffix = f"_{year}" if year else ""

    # ---- 数据准备 ----
    if "province" not in raw_df.columns:
        if raw_df.index.name in ("province", "省份"):
            raw_df = raw_df.reset_index()
        else:
            raise ValueError(
                f"raw_df 需要 'province' 列或同名 index，实际列: {list(raw_df.columns)}"
            )

    df = raw_df.copy()
    df["province"] = df["province"].astype(str)

    if indicator_cols is None:
        indicator_cols = [c for c in df.columns if c != "province"]
    indicator_cols = list(indicator_cols)

    # 预处理 + 归一化
    normed = _preprocess_indicators(df, indicator_cols)
    normed["province"] = df["province"].values
    normed = normed.set_index("province")

    if provinces is None:
        provinces = ["北京市", "上海市", "广东省", "江苏省", "浙江省"]

    missing = [p for p in provinces if p not in normed.index]
    if missing:
        print(f"[radar] 警告：以下省份未找到，已跳过 -> {missing}")
    provinces = [p for p in provinces if p in normed.index]
    if not provinces:
        raise ValueError("provinces 与数据全部不匹配，无法绘图。")

    # ---- 主图 ----
    main_png = _plot_radar(
        normed.loc[provinces, indicator_cols],
        indicator_cols,
        title=f"典型省份多维指标雷达图{('  ' + str(year) + '年') if year else ''}",
        save_path=out_dir / f"03_雷达图_{'_'.join(provinces[:5])}{suffix}.png",
    )

    # ---- 案例对比 ----
    case_png = None
    if case_pair is not None:
        a, b = case_pair
        if a in normed.index and b in normed.index:
            case_png = _plot_radar(
                normed.loc[[a, b], indicator_cols],
                indicator_cols,
                title=f"案例对比：{a} vs {b}{('  ' + str(year) + '年') if year else ''}",
                save_path=out_dir / f"04_雷达图_案例对比_{a}_vs_{b}{suffix}.png",
                colors=["#b8311a", "#4a7ab8"],
            )
        else:
            print(f"[radar] 案例对比省份缺失 ({a}, {b})，跳过")

    return {"main_png": main_png, "case_png": case_png}


def _plot_radar(
    sub_df: pd.DataFrame,
    indicators: Sequence[str],
    *,
    title: str,
    save_path: Path,
    colors: Optional[Sequence[str]] = None,
) -> Path:
    labels = [label_of(c) for c in indicators]
    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    palette = list(colors) if colors else PROVINCE_PALETTE

    for i, province in enumerate(sub_df.index):
        values = sub_df.loc[province, list(indicators)].tolist()
        values += values[:1]
        color = palette[i % len(palette)]
        ax.plot(angles, values, linewidth=2.2, label=province, color=color)
        ax.fill(angles, values, alpha=0.18, color=color)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.grid(alpha=0.4)
    ax.spines["polar"].set_alpha(0.35)
    ax.set_title(title, size=16, weight="bold", pad=24)
    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.28, 1.05),
        fontsize=11,
        frameon=True,
        framealpha=0.85,
    )

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"[radar] PNG 已生成: {save_path}")
    return save_path
