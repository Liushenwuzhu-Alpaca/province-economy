from src.data import get_indicators
from src.models.analyzer import analyze


def main(year: int = 2024, k: int = 4, use_pca: bool = True):
    """省域经济综合竞争力评价 -- 一键运行入口。

    流程:
        1. get_indicators(year)         → 获取 31 省 × 15 指标原始数据
        2. analyze(df, k=k, use_pca=?)  → 熵权评分 + K-Means 聚类
        3. 打印关键结论
    """
    print("=" * 60)
    print(f"  省域经济综合竞争力评价  (年份: {year})")
    print("=" * 60)

    df = get_indicators(year)
    print(f"\n[数据] 已加载 {df.shape[0]} 个省份, {df.shape[1]} 个指标\n")

    result = analyze(df, k=k, use_pca=use_pca)

    _print_method_a(result)
    _print_method_b(result, use_pca=use_pca)


def _print_method_a(result: dict):
    """打印方法A: 熵权评分排名。"""
    print("-" * 60)
    print("  方法A: 熵权法综合评分排名")
    print("-" * 60)

    # 指标权重
    print("\n[指标权重]")
    for indicator, weight in result["weights"].items():
        bar = "█" * int(weight * 200)
        print(f"  {indicator:25s}  {weight:>6.4f}  {bar}")

    # 排名前 10
    print("\n[TOP 10]")
    top10 = result["scores"].head(10)
    for _, row in top10.iterrows():
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(row["rank"], f"#{row['rank']}")
        print(f"  {medal:4s}  {row['province']:8s}  {row['score']:6.2f} 分")

    # 排名后 5
    print("\n[末尾 5]")
    bottom5 = result["scores"].tail(5)
    for _, row in bottom5.iterrows():
        print(f"  #{row['rank']:<3d}  {row['province']:8s}  {row['score']:6.2f} 分")


def _print_method_b(result: dict, use_pca: bool = True):
    """打印方法B: K-Means 聚类结果。"""
    method_label = "PCA 降维 + K-Means 聚类" if use_pca else "K-Means 聚类(无 PCA)"
    print("\n" + "-" * 60)
    print(f"  方法B: {method_label}")
    print("-" * 60)

    # PCA 信息 (仅启用时)
    pca_var = result.get("pca_var")
    if pca_var:
        print(f"\n[PCA] 前 2 主成分累计方差解释率: {sum(pca_var):.2%}")
        print(f"       PC1: {pca_var[0]:.2%}  PC2: {pca_var[1]:.2%}")

    # 聚类质量
    print(f"\n[聚类质量] Silhouette = {result['silhouette']:.4f}")

    # 各梯队分布
    print("\n[梯队分布]")
    labels = result["clusters"]["label"]
    for lb in sorted(labels.unique()):
        members = result["clusters"][labels == lb]["province"].tolist()
        tier_names = {
            0: "第一梯队(发达型)",
            1: "第二梯队(领先型)",
            2: "第三梯队(中坚型)",
            3: "第四梯队(追赶型)",
        }
        name = tier_names.get(lb, f"第{lb}梯队")
        print(f"\n  {name}  ({len(members)} 省):")
        print(f"    {'、'.join(members)}")

    print("\n" + "=" * 60)
    print("  分析完成。")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    use_pca = "--no-pca" not in sys.argv
    main(use_pca=use_pca)
