"""可视化通用工具：中文字体、配色、指标中文标签、输出路径。

所有四个绘图模块共用这里的样式，保证 PPT 中风格统一。
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager


# ---------------------------------------------------------------------------
# 1. 中文字体自适应
# ---------------------------------------------------------------------------

def setup_chinese_font() -> None:
    """根据操作系统自动选择中文字体。"""
    system = platform.system()
    if system == "Windows":
        candidates = ["Microsoft YaHei", "SimHei", "SimSun"]
    elif system == "Darwin":
        candidates = ["PingFang SC", "Heiti SC", "Hiragino Sans GB", "Arial Unicode MS"]
    else:
        candidates = [
            "Noto Sans CJK SC",
            "WenQuanYi Micro Hei",
            "WenQuanYi Zen Hei",
            "Source Han Sans CN",
            "SimHei",
        ]

    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates if c in available), None)

    if chosen:
        plt.rcParams["font.sans-serif"] = [chosen] + plt.rcParams["font.sans-serif"]
    else:
        plt.rcParams["font.sans-serif"] = candidates + plt.rcParams["font.sans-serif"]

    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["savefig.bbox"] = "tight"


# ---------------------------------------------------------------------------
# 2. 配色（PPT 主色调）
# ---------------------------------------------------------------------------

# 综合得分热力色阶：冷→暖
SCORE_COLORSCALE = [
    [0.00, "#2c5f8d"],
    [0.25, "#7fb2d8"],
    [0.50, "#f4e8c1"],
    [0.75, "#e89c5f"],
    [1.00, "#b8311a"],
]

# 聚类梯队配色（label 0→3 对应 reporter.TIER_NAMES）
TIER_COLOR_BY_LABEL = {
    0: "#b8311a",   # 第一梯队（发达型）
    1: "#e89c5f",   # 第二梯队（领先型）
    2: "#7fb2d8",   # 第三梯队（中坚型）
    3: "#2c5f8d",   # 第四梯队（追赶型）
    4: "#5b8c5a",   # 第五梯队（备用）
}

TIER_NAMES_BY_LABEL = {
    0: "第一梯队（发达型）",
    1: "第二梯队（领先型）",
    2: "第三梯队（中坚型）",
    3: "第四梯队（追赶型）",
    4: "第五梯队",
}

# 排名榜：金 / 银 / 铜
RANK_GOLD = "#d4af37"
RANK_SILVER = "#c0c0c0"
RANK_BRONZE = "#cd7f32"
RANK_NORMAL = "#4a7ab8"

# 多省份折线 / 雷达对比配色
PROVINCE_PALETTE = [
    "#b8311a", "#e89c5f", "#4a7ab8", "#5b8c5a",
    "#8e5a9b", "#c0793e", "#3d8e8e", "#a83279",
]


# ---------------------------------------------------------------------------
# 3. 指标 → 中文标签（与 ANALYSIS_INDICATORS 严格对齐）
# ---------------------------------------------------------------------------

INDICATOR_LABELS_CN = {
    "gdp": "GDP总量",
    "gdp_growth": "GDP增速",
    "retail": "社零总额",
    "income": "人均可支配收入",
    "consumption_expenditure": "人均消费支出",
    "tertiary_share": "第三产业占比",
    "fixed_invest": "固定资产投资",
    "fiscal_revenue": "财政收入",
    "cpi": "物价稳定度",      # 已转为 |CPI-100|
    "unemployment": "就业稳定度",  # 已反向
}


def label_of(indicator: str) -> str:
    """获取指标的中文显示标签。"""
    return INDICATOR_LABELS_CN.get(indicator, indicator)


# ---------------------------------------------------------------------------
# 4. 输出目录
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path("output")


def ensure_output_dir(output_dir: str | os.PathLike | None = None) -> Path:
    """确保输出目录存在并返回 Path 对象。"""
    path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# 5. 省份名规范化（GeoJSON 用全称）
# ---------------------------------------------------------------------------

PROVINCE_NAME_MAP = {
    "北京": "北京市", "上海": "上海市", "天津": "天津市", "重庆": "重庆市",
    "河北": "河北省", "山西": "山西省", "辽宁": "辽宁省", "吉林": "吉林省",
    "黑龙江": "黑龙江省", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
    "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
    "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "海南": "海南省",
    "四川": "四川省", "贵州": "贵州省", "云南": "云南省", "陕西": "陕西省",
    "甘肃": "甘肃省", "青海": "青海省", "台湾": "台湾省",
    "内蒙古": "内蒙古自治区", "广西": "广西壮族自治区", "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
    "香港": "香港特别行政区", "澳门": "澳门特别行政区",
}


def normalize_province_name(name: str) -> str:
    """统一为 DataV GeoJSON 中使用的省级行政区全称。"""
    if not isinstance(name, str):
        return name
    return PROVINCE_NAME_MAP.get(name.strip(), name.strip())
