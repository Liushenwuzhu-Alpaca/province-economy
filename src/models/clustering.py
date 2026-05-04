"""PCA 降维与 K-Means 聚类：省份发展模式分类。

方法B —— 回答："哪些省份的发展模式相近？"

先将高维指标空间压缩到 2 个主成分，再用 K-Means 对省份聚类。
结果揭示出简单排名无法捕捉的结构性分组。

典型解读:
    聚类 0 —— 高发展水平、服务业驱动型 (如北京、上海)
    聚类 1 —— 制造业驱动型 (如江苏、广东)
    聚类 2 —— 资源型或农业型经济
    聚类 3 —— 追赶中的发展中地区
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score


def cluster_analysis(
    std: pd.DataFrame,
    k: int = 4,
    random_state: int = 42,
    use_pca: bool = True,
) -> dict:
    """对标准化指标数据进行 K-Means 聚类, 可选 PCA 降维预处理。

    步骤:
        1. (可选) PCA 降到 2 个主成分, 去除指标间共线性。
        2. K-Means 聚类。
        3. 按各簇"综合水平"质心降序重排标签 (最高 → label 0)。
        4. Silhouette 系数评估聚类质量。

    参数:
        std: Z-Score 标准化后的指标 DataFrame。
             形状: (省份数, 指标数)
             行索引: 省份名称 (str)。
             列名: 指标代码 (str)。
        k: 聚类数量, 默认 4。
        random_state: 随机种子, 保证结果可复现。
        use_pca: 是否先用 PCA 降维再聚类。默认 True。

    返回:
        dict, 包含:
            clusters:    pd.DataFrame [province, label]
                         label 按发展水平排序 (0 = 最高)。
            pca_xy:      np.ndarray (n, 2) 或 None
                         前两个 PCA 坐标。不启用 PCA 时为 None。
            pca_var:     list 或 None
                         各主成分方差解释率。不启用 PCA 时为 None。
            silhouette:  float, [-1, 1], 越大聚类分离越好。
            centers:     np.ndarray
                         簇中心。启用 PCA 时形状 (k,2), 否则 (k,m)。
    """
    n, m = std.shape

    if n < k:
        raise ValueError("需要至少 %d 个省份以分成 %d 类, 当前仅有 %d 个" % (k, k, n))

    data = std.values

    # ---- 步骤 1: PCA 降维 (可选) ----
    if use_pca:
        n_components = min(2, m)
        pca = PCA(n_components=n_components, random_state=random_state)
        cluster_input = pca.fit_transform(data)
        pca_var = [round(v, 4) for v in pca.explained_variance_ratio_]
        pca_xy = cluster_input.copy()
    else:
        cluster_input = data
        pca_var = None
        pca_xy = None

    # ---- 步骤 2: K-Means 聚类 ----
    kmeans = KMeans(n_clusters=k, random_state=random_state, n_init="auto")
    labels_raw = kmeans.fit_predict(cluster_input)

    # ---- 步骤 3: 按综合水平重排标签 (越高 → label 越小) ----
    centers = kmeans.cluster_centers_
    if use_pca:
        # PCA 下 PC1 近似代表发展水平
        level_order = np.argsort(-centers[:, 0])
    else:
        # 无 PCA: 各簇所有指标均值之和代表综合水平
        level_order = np.argsort(-centers.sum(axis=1))
    label_map = {old: new for new, old in enumerate(level_order)}
    labels = np.array([label_map[l] for l in labels_raw])
    centers_ordered = centers[level_order]

    # ---- 步骤 4: Silhouette 系数 ----
    if k > 1 and n > k:
        sil = silhouette_score(cluster_input, labels)
    else:
        sil = 0.0

    clusters_df = pd.DataFrame({"province": std.index.tolist(), "label": labels})

    return {
        "clusters": clusters_df,
        "pca_xy": pca_xy,
        "pca_var": pca_var,
        "silhouette": round(sil, 4),
        "centers": centers_ordered,
    }
