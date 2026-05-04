"""分析结果缓存。

将每次分析的结果保存到 data/results/{year}_{pca|nopca}/ 目录。
二次运行自动加载缓存, 跳过重复计算。
"""

import json
from pathlib import Path

import pandas as pd


_RESULTS_DIR = Path(__file__).resolve().parents[2] / "data" / "results"


def _subdir(year: int, use_pca: bool) -> Path:
    suffix = "pca" if use_pca else "nopca"
    return _RESULTS_DIR / f"{year}_{suffix}"


def cache_valid(year: int, use_pca: bool) -> bool:
    """检查该年份/方法的缓存是否可用。"""
    sub = _subdir(year, use_pca)
    return (
        sub.exists()
        and (sub / "scores.csv").exists()
        and (sub / "clusters.csv").exists()
    )


def save_results(result: dict, year: int, use_pca: bool):
    """保存分析结果到磁盘。"""
    sub = _subdir(year, use_pca)
    sub.mkdir(parents=True, exist_ok=True)

    result["scores"].to_csv(sub / "scores.csv", index=False, encoding="utf-8-sig")
    result["clusters"].to_csv(sub / "clusters.csv", index=False, encoding="utf-8-sig")

    w = result["weights"]
    if isinstance(w, pd.Series):
        w = w.reset_index()
        w.columns = ["indicator", "weight"]
    w.to_csv(sub / "weights.csv", index=False, encoding="utf-8-sig")

    meta = {
        "year": year,
        "method": "pca" if use_pca else "nopca",
        "silhouette": result.get("silhouette"),
        "pca_var": [float(v) for v in result.get("pca_var") or []],
        "indicator_count": len(result.get("weights", [])),
    }
    (sub / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_results(year: int, use_pca: bool) -> dict:
    """从缓存加载分析结果。"""
    sub = _subdir(year, use_pca)
    scores = pd.read_csv(sub / "scores.csv", encoding="utf-8-sig")
    clusters = pd.read_csv(sub / "clusters.csv", encoding="utf-8-sig")
    weights = pd.read_csv(sub / "weights.csv", encoding="utf-8-sig")
    w_series = pd.Series(weights["weight"].values, index=weights["indicator"].values)
    meta = json.loads((sub / "meta.json").read_text(encoding="utf-8"))
    return {
        "scores": scores,
        "clusters": clusters,
        "weights": w_series,
        "silhouette": meta.get("silhouette"),
        "pca_var": meta.get("pca_var"),
    }
