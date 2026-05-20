from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(os.environ.get("PROJ_ROOT", Path(__file__).resolve().parents[1]))
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_CACHE_DIR = PROJECT_ROOT / "data_cache"


PROVINCES = [
    "北京市",
    "天津市",
    "河北省",
    "山西省",
    "内蒙古自治区",
    "辽宁省",
    "吉林省",
    "黑龙江省",
    "上海市",
    "江苏省",
    "浙江省",
    "安徽省",
    "福建省",
    "江西省",
    "山东省",
    "河南省",
    "湖北省",
    "湖南省",
    "广东省",
    "广西壮族自治区",
    "海南省",
    "重庆市",
    "四川省",
    "贵州省",
    "云南省",
    "西藏自治区",
    "陕西省",
    "甘肃省",
    "青海省",
    "宁夏回族自治区",
    "新疆维吾尔自治区",
]


PROVINCE_ALIASES = {
    "北京": "北京市",
    "天津": "天津市",
    "河北": "河北省",
    "山西": "山西省",
    "内蒙古": "内蒙古自治区",
    "辽宁": "辽宁省",
    "吉林": "吉林省",
    "黑龙江": "黑龙江省",
    "上海": "上海市",
    "江苏": "江苏省",
    "浙江": "浙江省",
    "安徽": "安徽省",
    "福建": "福建省",
    "江西": "江西省",
    "山东": "山东省",
    "河南": "河南省",
    "湖北": "湖北省",
    "湖南": "湖南省",
    "广东": "广东省",
    "广西": "广西壮族自治区",
    "海南": "海南省",
    "重庆": "重庆市",
    "四川": "四川省",
    "贵州": "贵州省",
    "云南": "云南省",
    "西藏": "西藏自治区",
    "陕西": "陕西省",
    "甘肃": "甘肃省",
    "青海": "青海省",
    "宁夏": "宁夏回族自治区",
    "新疆": "新疆维吾尔自治区",
}


INDICATORS = {
    "gdp": "地区生产总值(亿元)",
    "gdp_growth": "GDP增速(%)",
    "primary_value": "第一产业增加值(亿元)",
    "secondary_value": "第二产业增加值(亿元)",
    "tertiary_value": "第三产业增加值(亿元)",
    "primary_share": "第一产业占GDP比重(%)",
    "secondary_share": "第二产业占GDP比重(%)",
    "tertiary_share": "第三产业占GDP比重(%)",
    "retail": "社会消费品零售总额(亿元)",
    "income": "居民人均可支配收入(元)",
    "consumption_expenditure": "居民人均消费支出(元)",
    "cpi": "居民消费价格指数(上年=100)",
    "unemployment": "失业率代理指标(%)",
    "fixed_invest": "固定资产投资增速(%)",
    "fiscal_revenue": "地方一般公共预算收入(亿元)",
}


INDICATOR_UNITS = {
    "gdp": "亿元",
    "gdp_growth": "%",
    "primary_value": "亿元",
    "secondary_value": "亿元",
    "tertiary_value": "亿元",
    "primary_share": "%",
    "secondary_share": "%",
    "tertiary_share": "%",
    "retail": "亿元",
    "income": "元",
    "consumption_expenditure": "元",
    "cpi": "上年=100",
    "unemployment": "%",
    "fixed_invest": "%",
    "fiscal_revenue": "亿元",
}


INDICATOR_NOTES = {
    "gdp": "地区生产总值，按当年价格计算。",
    "gdp_growth": "由地区生产总值指数(上年=100)换算得到，计算方式为指数-100。",
    "primary_value": "第一产业增加值，按当年价格计算。",
    "secondary_value": "第二产业增加值，按当年价格计算。",
    "tertiary_value": "第三产业增加值，按当年价格计算；缺少官方第三产业列时由GDP-第一产业-第二产业计算。",
    "primary_share": "第一产业增加值/GDP*100。",
    "secondary_share": "第二产业增加值/GDP*100。",
    "tertiary_share": "第三产业增加值/GDP*100。",
    "retail": "社会消费品零售总额。",
    "income": "居民人均可支配收入。",
    "consumption_expenditure": "居民人均消费支出。",
    "cpi": "居民消费价格总指数。",
    "unemployment": "失业相关人数/(就业人员+失业相关人数)*100。2024年分子为年末领取失业保险金人数。",
    "fixed_invest": "固定资产投资比上年增长情况，替代原计划中的固定资产投资完成额。",
    "fiscal_revenue": "地方一般公共预算收入。",
}


REQUIRED_COLUMNS = ["province", "year", *INDICATORS.keys()]
