# 省域经济综合竞争力评价

本项目用于构建省域经济指标数据集，并在此基础上开展综合评价、聚类分析和可视化展示。

## 数据获取与清洗模块

当前已嵌入数据获取与清洗模块，统一入口为：

```python
from src.data import get_indicators

df = get_indicators(2024)
```

该接口会返回指定年份的省域经济指标数据。当前已整理 2023 年和 2024 年数据，覆盖 31 个省级行政区和 15 个指标。

数据来源包括：

- 国家统计局数据平台导出的官方 CSV；
- 《中国统计年鉴》官网 JPG 表格；
- OCR 解析后的年鉴中间数据；
- 本地清洗缓存结果。

数据目录说明见：

- `data/README.md`

数据抓取复现工具位于：

- `src/data/tools/download_yearbook_sources.py`
- `src/data/tools/parse_yearbook_images.py`

数据质量检查接口：

```python
from src.data import check_cached_indicators

report = check_cached_indicators(2024)
```

该检查会生成省份覆盖、指标列完整性和缺失值统计结果。

指标清洗检查接口位于 `src/indicators`：

```python
from src.data import get_indicators
from src.indicators import quality_report

df = get_indicators(2024)
report = quality_report(df)
```

该模块负责对清洗后的指标数据进行质量检查，包括省份覆盖、重复省份、指标列完整性和缺失值统计。

## 当前指标

当前数据表包含以下 15 个指标：

- `gdp`：地区生产总值，亿元。
- `gdp_growth`：GDP 增速，%。
- `primary_value`：第一产业增加值，亿元。
- `secondary_value`：第二产业增加值，亿元。
- `tertiary_value`：第三产业增加值，亿元。
- `primary_share`：第一产业占 GDP 比重，%。
- `secondary_share`：第二产业占 GDP 比重，%。
- `tertiary_share`：第三产业占 GDP 比重，%。
- `retail`：社会消费品零售总额，亿元。
- `income`：居民人均可支配收入，元。
- `consumption_expenditure`：居民人均消费支出，元。
- `cpi`：居民消费价格指数，上年=100。
- `unemployment`：失业率代理指标，%。
- `fixed_invest`：固定资产投资增速，%。
- `fiscal_revenue`：地方一般公共预算收入，亿元。

## 运行示例

```bash
uv run python main.py
```
