"""熵权法：客观赋权与综合评分。

方法A —— 回答："哪个省排名更高？"

熵权法根据指标内部的信息离散程度自动分配权重：各省之间差异越大
的指标获得权重越高。整个过程无需任何主观判断。

"""

import numpy as np
import pandas as pd


def entropy_weight(normed: pd.DataFrame) -> dict:
    """基于信息熵计算客观权重与综合得分。

    计算步骤:
        1. 计算比重矩阵:    p_ij = x_ij / sum_i(x_ij)
        2. 计算信息熵:      e_j = -k * sum_i(p_ij * ln(p_ij))
        3. 计算差异系数:    d_j = 1 - e_j
        4. 归一化为权重:    w_j = d_j / sum(d_j)
        5. 加权综合得分:    s_i = sum_j(w_j * x_ij) * 100

    参数:
        normed: Min-Max 归一化后的指标 DataFrame。
                形状: (省份数, 指标数)
                行索引: 省份名称 (str)。
                列名: 指标代码 (str)。
                所有值必须在 [0, 1] 之间, 且值越大越好。
                负向指标必须在传入前做反向处理。

    返回:
        dict, 包含:
            scores:  pd.DataFrame, 列 [province, score, rank]
                     按排名升序排列。score 取值范围 [0, 100]。
            weights: pd.Series, 索引=指标名, 值=权重 (总和为 1)。
    """
    n, m = normed.shape

    # 守卫：熵权法至少需要 2 个评价对象
    if n < 2:
        raise ValueError("熵权法至少需要 2 个省份, 当前仅有 %d 个" % n)

    # ---- 步骤 1: 比重矩阵 ----
    # p_ij = x_ij / sum_i(x_ij)
    col_sums = normed.sum(axis=0)
    # 防止除零：某指标全为 0 时视为无信息 (后续权重趋于 0)
    col_sums = col_sums.replace(0, 1.0)
    p = normed.div(col_sums, axis=1)

    # ---- 步骤 2: 信息熵 ----
    # e_j = -k * sum(p_ij * ln(p_ij))
    # k = 1 / ln(n), 使熵值落在 [0, 1] 之间
    k = 1.0 / np.log(n)
    # log(0) → NaN, skipna=True 时 sum 将其视为 0 —— 数学上正确
    entropy = -k * (p * np.log(p.replace(0, np.nan))).sum(axis=0, skipna=True)

    # ---- 步骤 3: 差异系数 ----
    # d_j = 1 - e_j (差异越大 → d 越大 → 权重越大)
    d = 1.0 - entropy

    # ---- 步骤 4: 归一化为权重 ----
    d_sum = d.sum()
    if d_sum < 1e-10:
        # 所有指标差异系数均接近 0 → 等权重兜底
        weights = pd.Series(1.0 / m, index=normed.columns, name="weight")
    else:
        weights = (d / d_sum).rename("weight")

    # ---- 步骤 5: 加权综合得分 ----
    scores_raw = normed.dot(weights)

    # 将原始得分线性映射到 [0, 100] 方便阅读
    raw_min, raw_max = scores_raw.min(), scores_raw.max()
    if raw_max - raw_min < 1e-10:
        # 所有省份得分一致 → 统一给 50 分
        scores_scaled = pd.Series(50.0, index=normed.index)
    else:
        scores_scaled = (scores_raw - raw_min) / (raw_max - raw_min) * 100.0

    # 构建输出 DataFrame
    scores_df = (
        pd.DataFrame(
            {
                "province": normed.index,
                "score": scores_scaled.round(2).values,
                "rank": scores_scaled.rank(ascending=False, method="min").astype(int),
            }
        )
        .sort_values("rank")
        .reset_index(drop=True)
    )

    return {
        "scores": scores_df,
        "weights": weights.round(4),
    }
