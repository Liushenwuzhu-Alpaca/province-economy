# 数据抓取与清洗模块

本模块负责将国家统计局和统计年鉴中的原始数据整理为后续模型可以直接使用的标准化指标表。

## 快速上手

```bash
# 安装依赖
uv sync

# 获取数据
uv run python -c "
from src.data import get_indicators

df = get_indicators(2024)
print(df.shape)    # (31, 15)
print(df.head())
"
```

## 对外接口

### `get_indicators(year)`

```python
from src.data import get_indicators

df = get_indicators(2024)  # 支持 2019-2024 任意年份
```

**参数**: `year` — 整数，取值 2019/2020/2021/2022/2023/2024

**返回**: `pandas.DataFrame`
- 行索引: `province`（31 个省级行政区全称）
- 列: 15 个经济指标（全部数值型，无缺失值）
- 缺失值已用中位数填补

**返回示例**:

```
              gdp  gdp_growth  primary_value  ...  unemployment  fixed_invest  fiscal_revenue
province                                          ...
北京市    49670.2         5.1          112.2  ...       2.434767           3.2         6372.68
天津市    17931.3         4.9          284.5  ...       1.887960           5.1         2134.20
河北省    47448.1         5.4         4498.1  ...       0.278690           3.1         4310.85
...
```

**缓存机制**: 首次调用会从 `data/raw/ocr_outputs/` 读取原始数据并清洗，结果缓存到 `data_cache/indicators_{year}.csv`。后续调用直接读缓存。传 `refresh=True` 可强制重算。

### `missing_value_report(df)`

```python
from src.data import missing_value_report

report = missing_value_report(get_indicators(2024))
print(report)
```

返回每列的缺失值统计。

## 15 个指标说明

| 代码 | 中文名称 | 单位 | 说明 |
|------|---------|------|------|
| `gdp` | 地区生产总值 | 亿元 | 按当年价格计算 |
| `gdp_growth` | GDP增速 | % | 由GDP指数(上年=100)换算：指数 - 100 |
| `primary_value` | 第一产业增加值 | 亿元 | 按当年价格计算 |
| `secondary_value` | 第二产业增加值 | 亿元 | 按当年价格计算 |
| `tertiary_value` | 第三产业增加值 | 亿元 | 缺少官方数据时由 GDP - 第一 - 第二 计算 |
| `primary_share` | 第一产业占GDP比重 | % | 第一产业增加值 / GDP × 100 |
| `secondary_share` | 第二产业占GDP比重 | % | 第二产业增加值 / GDP × 100 |
| `tertiary_share` | 第三产业占GDP比重 | % | 第三产业增加值 / GDP × 100 |
| `retail` | 社会消费品零售总额 | 亿元 | |
| `income` | 居民人均可支配收入 | 元 | |
| `consumption_expenditure` | 居民人均消费支出 | 元 | |
| `cpi` | 居民消费价格指数 | 上年=100 | 100 代表物价不变 |
| `unemployment` | 失业率代理指标 | % | 城镇登记失业人数 / (城镇就业人员 + 失业人数) × 100 |
| `fixed_invest` | 固定资产投资增速 | % | 比上年增长 |
| `fiscal_revenue` | 地方一般公共预算收入 | 亿元 | |

> 模型层从中选取 10 个核心指标进行分析，定义见 `src/models/analyzer.py` 的 `ANALYSIS_INDICATORS`。

## 模块文件

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 `get_indicators`、`create_template`、`missing_value_report` |
| `fetcher.py` | 统一调度：缓存读取 → 原始数据读取 → NBS CSV 合并 → 清洗 → 缓存写入 |
| `cleaner.py` | 省份名称标准化、数值清洗、31 省完整性检查、缺失值中位数填补 |
| `nbs_exports.py` | 读取 `data/raw/nbs_exports/` 中的官方 CSV，按年份提取指标列 |
| `nbs_yearbook.py` | 从中国统计年鉴官网定位并下载 JPG 表格图片 |
| `yearbook_ocr.py` | OCR 解析年鉴 JPG 表格，提取分省数据 |
| `tools/` | 鉴于图片下载和 OCR 解析的复现脚本 |

## 数据来源

1. **国家统计局导出 CSV** (`data/raw/nbs_exports/`) — 主要来源，覆盖 2019-2024 大部分指标
2. **统计年鉴 JPG + OCR** — 用于补充 CSV 中缺失的指标（零售总额、财政、投资、失业等），仅 2023/2024
3. **缓存** (`data_cache/`) — 清洗后自动生成，避免重复解析
