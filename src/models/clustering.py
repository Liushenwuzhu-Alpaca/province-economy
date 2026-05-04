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
) -> dict:
    """对标准化指标数据进行 PCA 降维和 K-Means 聚类。

    步骤:
        1. 用 PCA 将数据降到 2 个主成分。
        2. 在这 2 个主成分上运行 K-Means 聚类。
        3. 按 PC1 质心降序重排标签 (最高 → label 0)。
        4. 计算 Silhouette 系数评估聚类质量。

    参数:
        std: Z-Score 标准化后的指标 DataFrame。
             形状: (省份数, 指标数)
             行索引: 省份名称 (str)。
             列名: 指标代码 (str)。
             值以 0 为中心, 具有单位方差。
        k: 聚类数量, 默认 4。
        random_state: 随机种子, 保证结果可复现。

    返回:
        dict, 包含:
            clusters:    pd.DataFrame, 列 [province, label]。
                         label 按发展水平排序 (0 = 最高梯队)。
            pca_xy:      np.ndarray, 形状 (n, 2), 前两个主成分坐标。
            pca_var:     list, 各主成分的方差解释率。
            silhouette:  float, 范围 [-1, 1], 越大聚类分离越好。
            centers:     np.ndarray, 形状 (k, 2), PCA 空间中的簇中心。
    """
    n, m = std.shape

    # 守卫：省份数不能少于聚类数
    if n < k:
        raise ValueError("需要至少 %d 个省份以分成 %d 类, 当前仅有 %d 个" % (k, k, n))

    # ---- 步骤 1: PCA 降维 ----
    n_components = min(2, m)
    pca = PCA(n_components=n_components, random_state=random_state)
    pca_xy = pca.fit_transform(std.values)

    # ---- 步骤 2: K-Means 聚类 ----
    kmeans = KMeans(n_clusters=k, random_state=random_state, n_init="auto")
    labels_raw = kmeans.fit_predict(pca_xy)

    # ---- 步骤 3: 按 PC1 质心重排标签 (PC1 越高 → label 越小) ----
    # PC1 通常代表"综合发展水平", 所以 PC1 质心更高的簇应获得更小的标签
    centers = kmeans.cluster_centers_
    pc1_order = np.argsort(-centers[:, 0])  # PC1 降序排列
    label_map = {old: new for new, old in enumerate(pc1_order)}
    labels = np.array([label_map[l] for l in labels_raw])

    # 同步重排中心点
    centers_ordered = centers[pc1_order]

    # ---- 步骤 4: Silhouette 系数 ----
    if k > 1 and n > k:
        sil = silhouette_score(pca_xy, labels)
    else:
        sil = 0.0

    # ---- 构建输出 ----
    clusters_df = pd.DataFrame({"province": std.index.tolist(), "label": labels})

    return {
        "clusters": clusters_df,
        "pca_xy": pca_xy,
        "pca_var": [round(v, 4) for v in pca.explained_variance_ratio_],
        "silhouette": round(sil, 4),
        "centers": centers_ordered,
    }
