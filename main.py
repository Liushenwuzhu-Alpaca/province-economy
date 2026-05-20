"""省域经济综合竞争力评价 -- 运行入口。

用法:
    python main.py                     # 默认 2024, PCA, 缓存优先
    python main.py --year 2023          # 指定年份
    python main.py --recompute          # 跳过缓存, 强制重算
    python main.py --no-pca             # 跳过 PCA 降维
"""

import sys
import pandas as pd

from src.data import get_indicators
from src.models.analyzer import analyze
from src.models.cache import cache_valid, load_results, save_results
from src.models.reporter import print_method_a, print_method_b


YEAR_LIST = {2019, 2020, 2021, 2022, 2023, 2024}


def main(year: int = 2024, k: int = 4, use_pca: bool = True, recompute: bool = False):
    print("=" * 60)
    print(f"  省域经济综合竞争力评价  (年份: {year})")
    print("=" * 60)

    if year not in YEAR_LIST:
        print(f"\n错误: {year} 年数据不存在 (可用: {YEAR_LIST})")
        return

    method_key = "pca" if use_pca else "nopca"

    if not recompute and cache_valid(year, use_pca):
        print(f"\n[缓存] 已加载已有结果 (data/results/{year}_{method_key}/)")
        result = load_results(year, use_pca)
    else:
        df = get_indicators(year)
        print(f"\n[数据] 已加载 {df.shape[0]} 个省份, {df.shape[1]} 个指标\n")
        result = analyze(df, k=k, use_pca=use_pca)
        save_results(result, year, use_pca)
        print(f"[缓存] 结果已保存至 data/results/{year}_{method_key}/\n")

    print_method_a(result)
    print_method_b(result, use_pca=use_pca)


def _parse_args() -> dict:
    args = {"year": 2024, "use_pca": True, "recompute": False}
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--no-pca":
            args["use_pca"] = False
        elif a == "--recompute":
            args["recompute"] = True
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
    main(year=opts["year"], use_pca=opts["use_pca"], recompute=opts["recompute"])
