"""省域经济综合竞争力评价 -- 运行入口。

用法:
    python main.py                          # 默认 2024, PCA, 缓存优先
    python main.py --year 2023              # 指定年份
    python main.py --recompute              # 跳过缓存, 强制重算
    python main.py --no-pca                 # 跳过 PCA 降维
    python main.py --viz                    # 同时渲染所有图表到 output/
    python main.py --all-years --viz        # 跑全部年份并生成趋势图
"""

import sys

from src.data import get_indicators
from src.models.analyzer import analyze
from src.models.cache import cache_valid, load_results, save_results
from src.models.reporter import print_method_a, print_method_b


YEAR_LIST = {2019, 2020, 2021, 2022, 2023, 2024}


def _run_year(year: int, k: int, use_pca: bool, recompute: bool) -> tuple[dict, "pd.DataFrame"]:
    """执行单年份分析并返回 (result, raw_df)。"""
    method_key = "pca" if use_pca else "nopca"

    if not recompute and cache_valid(year, use_pca):
        print(f"\n[缓存] 已加载已有结果 (data/results/{year}_{method_key}/)")
        result = load_results(year, use_pca)
    else:
        raw_df = get_indicators(year)
        print(f"\n[数据] 已加载 {raw_df.shape[0]} 个省份, {raw_df.shape[1]} 个指标\n")
        result = analyze(raw_df, k=k, use_pca=use_pca)
        save_results(result, year, use_pca)
        print(f"[缓存] 结果已保存至 data/results/{year}_{method_key}/\n")

    # 雷达图需要原始指标，强制重新拉一次（akshare 有缓存，几乎不耗时）
    raw_df = get_indicators(year)
    return result, raw_df


def main(
    year: int = 2024,
    k: int = 4,
    use_pca: bool = True,
    recompute: bool = False,
    viz: bool = False,
    all_years: bool = False,
):
    print("=" * 60)
    print(f"  省域经济综合竞争力评价 (年份: {'全部' if all_years else year})")
    print("=" * 60)

    if all_years:
        target_years = sorted(YEAR_LIST)
    else:
        if year not in YEAR_LIST:
            print(f"\n错误: {year} 年数据不存在 (可用: {YEAR_LIST})")
            return
        target_years = [year]

    yearly_results: dict = {}
    yearly_raw_df: dict = {}

    for y in target_years:
        result, raw_df = _run_year(y, k, use_pca, recompute)
        yearly_results[y] = result
        yearly_raw_df[y] = raw_df

        print_method_a(result)
        print_method_b(result, use_pca=use_pca)

    # ---- 可视化 ----
    if viz:
        from src.visualization import render_all
        render_all(yearly_results, yearly_raw_df)


def _parse_args() -> dict:
    args = {
        "year": 2024,
        "use_pca": True,
        "recompute": False,
        "viz": False,
        "all_years": False,
    }
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--no-pca":
            args["use_pca"] = False
        elif a == "--recompute":
            args["recompute"] = True
        elif a == "--viz":
            args["viz"] = True
        elif a == "--all-years":
            args["all_years"] = True
        elif a in ("--year", "-y"):
            if i + 1 < len(sys.argv):
                args["year"] = int(sys.argv[i + 1])
                i += 1
        elif a.isdigit():
            args["year"] = int(a)
        i += 1
    return args


if __name__ == "__main__":
    opts = _parse_args()
    main(
        year=opts["year"],
        use_pca=opts["use_pca"],
        recompute=opts["recompute"],
        viz=opts["viz"],
        all_years=opts["all_years"],
    )
