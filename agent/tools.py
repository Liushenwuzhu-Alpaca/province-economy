"""Data query tools for the province economy Agent.

These tools read directly from cached CSV results and indicator data,
providing structured responses for the Claude Agent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"
CACHE_DIR = Path(__file__).parent.parent / "data_cache"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

INDICATOR_LABELS = {
    "gdp": "GDP(亿元)",
    "gdp_growth": "GDP增速(%)",
    "retail": "社会消费品零售总额(亿元)",
    "income": "居民人均可支配收入(元)",
    "consumption_expenditure": "居民人均消费支出(元)",
    "tertiary_share": "第三产业占比(%)",
    "fixed_invest": "固定资产投资增速(%)",
    "fiscal_revenue": "地方一般公共预算收入(亿元)",
    "cpi": "CPI(上年=100)",
    "unemployment": "失业率代理(%)",
}


def _year_dir(year: int) -> Path:
    return RESULTS_DIR / f"{year}_pca"


def _check_year(year: int) -> str | None:
    if year not in YEARS:
        return f"不支持年份 {year}，可选: {YEARS}"
    if not _year_dir(year).exists():
        return f"{year} 年数据尚未计算"
    return None


# ---------- Tool 1: 排名查询 ----------

def get_ranking(year: int, top_n: int = 10) -> str:
    """获取某年的综合得分排名。

    Args:
        year: 年份 (2019-2024)
        top_n: 返回前N名，默认10，0表示全部
    """
    err = _check_year(year)
    if err:
        return err

    scores = pd.read_csv(_year_dir(year) / "scores.csv")
    if top_n > 0:
        scores = scores.head(top_n)

    lines = [f"## {year}年综合得分排名（前{top_n}名）\n"]
    for _, row in scores.iterrows():
        lines.append(f"{int(row['rank'])}. {row['province']} — {row['score']:.2f}分")
    return "\n".join(lines)


# ---------- Tool 2: 省份详情 ----------

def get_province_detail(province: str, year: int) -> str:
    """获取某省某年的所有指标数据。

    Args:
        province: 省份全称（如"广东省"）
        year: 年份
    """
    cache_file = CACHE_DIR / f"indicators_{year}.csv"
    if not cache_file.exists():
        return f"{year}年指标数据不存在"

    df = pd.read_csv(cache_file)
    row = df[df["province"] == province]
    if row.empty:
        # 尝试模糊匹配
        matches = df[df["province"].str.contains(province[:2])]
        if not matches.empty:
            row = matches.head(1)
        else:
            return f"未找到省份「{province}」"

    row = row.iloc[0]
    lines = [f"## {province} {year}年指标数据\n"]
    for col in row.index:
        if col == "province":
            continue
        label = INDICATOR_LABELS.get(col, col)
        val = row[col]
        if pd.notna(val):
            lines.append(f"- {label}: {val}")

    # 补充排名信息
    scores_file = _year_dir(year) / "scores.csv"
    if scores_file.exists():
        scores = pd.read_csv(scores_file)
        match = scores[scores["province"] == province]
        if not match.empty:
            lines.append(f"\n综合排名: 第{int(match.iloc[0]['rank'])}名，得分{match.iloc[0]['score']:.2f}")

    return "\n".join(lines)


# ---------- Tool 3: 梯队查询 ----------

def get_cluster_members(year: int, label: int | None = None) -> str:
    """获取某年的聚类梯队成员。

    Args:
        year: 年份
        label: 梯队编号 0-3（0=最发达），None表示返回全部
    """
    err = _check_year(year)
    if err:
        return err

    clusters = pd.read_csv(_year_dir(year) / "clusters.csv")
    tier_names = {0: "第一梯队(发达型)", 1: "第二梯队(领先型)", 2: "第三梯队(中坚型)", 3: "第四梯队(追赶型)"}

    # 读取meta获取silhouette
    meta_file = _year_dir(year) / "meta.json"
    meta = {}
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))

    lines = [f"## {year}年聚类分析"]
    if meta.get("silhouette"):
        lines.append(f"Silhouette系数: {meta['silhouette']:.4f}\n")

    if label is not None:
        members = clusters[clusters["label"] == label]
        name = tier_names.get(label, f"梯队{label}")
        lines.append(f"{name}({len(members)}省): {', '.join(members['province'].tolist())}")
    else:
        for lbl in sorted(clusters["label"].unique()):
            members = clusters[clusters["label"] == lbl]
            name = tier_names.get(lbl, f"梯队{lbl}")
            lines.append(f"{name}({len(members)}省): {', '.join(members['province'].tolist())}")

    return "\n".join(lines)


# ---------- Tool 4: 指标权重 ----------

def get_weights(year: int) -> str:
    """获取某年的熵权法指标权重。

    Args:
        year: 年份
    """
    err = _check_year(year)
    if err:
        return err

    weights = pd.read_csv(_year_dir(year) / "weights.csv")
    lines = [f"## {year}年熵权法指标权重\n"]
    for _, row in weights.sort_values("weight", ascending=False).iterrows():
        ind = row["indicator"]
        label = INDICATOR_LABELS.get(ind, ind)
        lines.append(f"- {label}: {row['weight']:.4f}")
    return "\n".join(lines)


# ---------- Tool 5: 跨年对比 ----------

def compare_years(province: str) -> str:
    """查看某省在所有年份的排名和得分变化。

    Args:
        province: 省份全称
    """
    lines = [f"## {province} 跨年排名对比\n"]
    lines.append("| 年份 | 排名 | 得分 |")
    lines.append("|------|------|------|")

    for year in YEARS:
        scores_file = _year_dir(year) / "scores.csv"
        if not scores_file.exists():
            continue
        scores = pd.read_csv(scores_file)
        match = scores[scores["province"] == province]
        if match.empty:
            matches = scores[scores["province"].str.contains(province[:2])]
            if not matches.empty:
                match = matches.head(1)
        if not match.empty:
            r = match.iloc[0]
            lines.append(f"| {year} | {int(r['rank'])} | {r['score']:.2f} |")

    return "\n".join(lines)


# ---------- Tool 6: RAG知识检索 ----------

def search_knowledge(query: str, top_k: int = 5) -> str:
    """在知识库中语义检索相关内容。

    Args:
        query: 搜索问题
        top_k: 返回条数
    """
    from agent.rag import get_context
    context = get_context(query, top_k)
    if not context:
        return "知识库中未找到相关内容"
    return context


# ---------- Tool registry for Claude ----------

TOOL_DEFINITIONS = [
    {
        "name": "get_ranking",
        "description": "获取某年的综合得分排名。回答'谁排第几'类问题。",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "年份 (2019-2024)"},
                "top_n": {"type": "integer", "description": "返回前N名，默认10，0=全部", "default": 10},
            },
            "required": ["year"],
        },
    },
    {
        "name": "get_province_detail",
        "description": "获取某省某年的全部经济指标数据和排名。回答'某省具体情况'类问题。",
        "input_schema": {
            "type": "object",
            "properties": {
                "province": {"type": "string", "description": "省份全称，如'广东省'"},
                "year": {"type": "integer", "description": "年份 (2019-2024)"},
            },
            "required": ["province", "year"],
        },
    },
    {
        "name": "get_cluster_members",
        "description": "获取某年的聚类梯队成员。回答'第一梯队有哪些省'、'哪些省发展模式相近'类问题。",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "年份 (2019-2024)"},
                "label": {"type": "integer", "description": "梯队编号0-3 (0=最发达)，不填返回全部", "default": None},
            },
            "required": ["year"],
        },
    },
    {
        "name": "get_weights",
        "description": "获取某年的熵权法指标权重。回答'哪个指标权重最高'、'为什么排名是这样'类问题。",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "年份 (2019-2024)"},
            },
            "required": ["year"],
        },
    },
    {
        "name": "compare_years",
        "description": "查看某省在所有年份的排名变化。回答'某省排名怎么变化'类问题。",
        "input_schema": {
            "type": "object",
            "properties": {
                "province": {"type": "string", "description": "省份全称，如'广东省'"},
            },
            "required": ["province"],
        },
    },
    {
        "name": "search_knowledge",
        "description": "在知识库中语义检索相关内容。用于回答需要背景知识、方法论解释、历史事件等无法从数据直接获取的问题。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索问题或关键词"},
                "top_k": {"type": "integer", "description": "返回条数，默认5", "default": 5},
            },
            "required": ["query"],
        },
    },
]

# Map tool name → function
TOOL_MAP = {
    "get_ranking": get_ranking,
    "get_province_detail": get_province_detail,
    "get_cluster_members": get_cluster_members,
    "get_weights": get_weights,
    "compare_years": compare_years,
    "search_knowledge": search_knowledge,
}
