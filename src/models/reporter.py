"""打印分析结果。"""

import pandas as pd


TIER_NAMES = {
    0: "第一梯队(发达型)",
    1: "第二梯队(领先型)",
    2: "第三梯队(中坚型)",
    3: "第四梯队(追赶型)",
}


def print_method_a(result: dict):
    """打印方法A: 熵权评分排名。"""
    print("-" * 60)
    print("  方法A: 熵权法综合评分排名")
    print("-" * 60)

    print("\n[指标权重]")
    for indicator, weight in result["weights"].items():
        bar = "█" * int(weight * 200)
        print(f"  {indicator:25s}  {weight:>6.4f}  {bar}")

    print("\n[TOP 10]")
    top10 = result["scores"].head(10)
    for _, row in top10.iterrows():
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(row["rank"], f"#{row['rank']}")
        print(f"  {medal:4s}  {row['province']:8s}  {row['score']:6.2f} 分")

    print("\n[末尾 5]")
    bottom5 = result["scores"].tail(5)
    for _, row in bottom5.iterrows():
        print(f"  #{row['rank']:<3d}  {row['province']:8s}  {row['score']:6.2f} 分")


def print_method_b(result: dict, use_pca: bool = True):
    """打印方法B: K-Means 聚类结果。"""
    label = "PCA 降维 + K-Means 聚类" if use_pca else "K-Means 聚类(无 PCA)"
    print("\n" + "-" * 60)
    print(f"  方法B: {label}")
    print("-" * 60)

    pca_var = result.get("pca_var")
    if pca_var:
        print(f"\n[PCA] 前 2 主成分累计方差解释率: {sum(pca_var):.2%}")
        print(f"       PC1: {pca_var[0]:.2%}  PC2: {pca_var[1]:.2%}")

    print(f"\n[聚类质量] Silhouette = {result['silhouette']:.4f}")

    print("\n[梯队分布]")
    labels = result["clusters"]["label"]
    for lb in sorted(labels.unique()):
        members = result["clusters"][labels == lb]["province"].tolist()
        name = TIER_NAMES.get(lb, f"第{lb}梯队")
        print(f"\n  {name}  ({len(members)} 省):")
        print(f"    {'、'.join(members)}")

    print("\n" + "=" * 60)
    print("  分析完成。")
    print("=" * 60)
