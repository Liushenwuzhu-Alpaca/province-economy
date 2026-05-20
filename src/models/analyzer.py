"""数据层与模型层的桥接模块。

负责:
    1. 从全部指标中选取核心分析指标
    2. 定义指标方向 (正向/负向)
    3. 归一化 (Min-Max 给熵权法, Z-Score 给 PCA/K-Means)
    4. 调用两种模型, 合并返回结果
"""

import numpy as np
import pandas as pd

from .entropy import entropy_weight
from .clustering import cluster_analysis


# ---- 分析用指标和方向定义 ----

# 10 个指标
ANALYSIS_INDICATORS = [
    "gdp",  # 地区生产总值
    "gdp_growth",  # GDP增速
    "retail",  # 社会消费品零售总额
    "income",  # 居民人均可支配收入
    "consumption_expenditure",  # 居民人均消费支出
    "tertiary_share",  # 第三产业占GDP比重
    "fixed_invest",  # 固定资产投资增速
    "fiscal_revenue",  # 地方一般公共预算收入
    "cpi",  # 居民消费价格指数 (特殊处理)
    "unemployment",  # 失业率代理指标
]

# 方向定义: 1=正向(越大越好), -1=负向(越小越好)
DIRECTIONS = {
    "gdp": 1,
    "gdp_growth": 1,
    "retail": 1,
    "income": 1,
    "consumption_expenditure": 1,
    "tertiary_share": 1,
    "fixed_invest": 1,
    "fiscal_revenue": 1,
    "cpi": -1,  # 偏离 100 越远越差
    "unemployment": -1,  # 失业率越低越好
}

# 建议的聚类数量
DEFAULT_K = 4


def _prepare_cpi(df: pd.DataFrame) -> pd.DataFrame:
    """CPI 特殊处理：转换为偏离 100 的绝对值。

    CPI = 100 代表物价稳定, >100 通胀, <100 通缩。
    均视为不利, 因此取 |CPI - 100| 作为负向指标。
    """
    df = df.copy()
    if "cpi" in df.columns:
        df["cpi"] = (df["cpi"] - 100.0).abs()
    return df


def _minmax_normalize(df: pd.DataFrame, directions: dict) -> pd.DataFrame:
    """Min-Max 归一化, 同步处理方向。

    步骤:
        1. 负向指标做反向处理 (max - x)
        2. 全部指标缩放到 [0, 1]

    返回:
        归一化后的 DataFrame, 所有值在 [0, 1] 之间, 且都是正向含义。
    """
    normed = df.copy()

    # 反向处理负向指标
    for col, d in directions.items():
        if col not in normed.columns:
            continue
        if d == -1:
            col_max = normed[col].max()
            normed[col] = col_max - normed[col]

    # Min-Max 缩放到 [0, 1]
    for col in normed.columns:
        col_min, col_max = normed[col].min(), normed[col].max()
        rng = col_max - col_min
        if rng < 1e-10:
            normed[col] = 0.5  # 所有省该指标相同 → 中性值
        else:
            normed[col] = (normed[col] - col_min) / rng

    return normed


def _zscore_standardize(df: pd.DataFrame, directions: dict) -> pd.DataFrame:
    """Z-Score 标准化, 同步处理方向。

    步骤:
        1. 负向指标做反向处理 (max - x)
        2. 全部指标标准化为均值 0、标准差 1

    返回:
        标准化后的 DataFrame。
    """
    std = df.copy()

    # 反向处理负向指标
    for col, d in directions.items():
        if col not in std.columns:
            continue
        if d == -1:
            col_max = std[col].max()
            std[col] = col_max - std[col]

    # Z-Score 标准化
    for col in std.columns:
        mean = std[col].mean()
        s = std[col].std(ddof=1)
        if s < 1e-10:
            std[col] = 0.0
        else:
            std[col] = (std[col] - mean) / s

    return std


def analyze(
    raw_df: pd.DataFrame,
    indicators: list | None = None,
    k: int = DEFAULT_K,
    use_pca: bool = True,
) -> dict:
    """运行双方法分析：熵权评分 + K-Means 聚类(可选 PCA)。

    参数:
        raw_df:      get_indicators() 的返回值。
        indicators:  要用到的指标列名列表。默认 ANALYSIS_INDICATORS。
        k:           聚类数量, 默认 4。
        use_pca:     True=先用 PCA 降维再聚类, False=直接对 10 维数据聚类。

    返回:
        dict:
            scores, weights, clusters, pca_xy, pca_var, silhouette, centers
            use_pca=False 时 pca_xy 和 pca_var 为 None。
    """
    # ---- 指标选取 ----
    if indicators is None:
        indicators = ANALYSIS_INDICATORS

    available = [c for c in indicators if c in raw_df.columns]
    missing = set(indicators) - set(available)
    if missing:
        print(f"[analyze] 警告: 以下指标不存在, 已跳过: {missing}")

    df = raw_df[available].copy()
    dirs = {k: v for k, v in DIRECTIONS.items() if k in available}

    # CPI 特殊处理: 偏离 100 的绝对值
    df = _prepare_cpi(df)

    # ---- 方法A: 熵权法 ----
    normed = _minmax_normalize(df, dirs)
    result_a = entropy_weight(normed)

    # ---- 方法B: K-Means (可选 PCA) ----
    std = _zscore_standardize(df, dirs)
    result_b = cluster_analysis(std, k=k, use_pca=use_pca)

    return {
        "scores": result_a["scores"],
        "weights": result_a["weights"],
        "clusters": result_b["clusters"],
        "pca_xy": result_b["pca_xy"],
        "pca_var": result_b["pca_var"],
        "silhouette": result_b["silhouette"],
        "centers": result_b["centers"],
    }
