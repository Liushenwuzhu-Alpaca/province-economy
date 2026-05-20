# visualization — 省域经济静态可视化

基于 Matplotlib 的图表包，生成 **PNG 图片 + 嵌入式 HTML**，可直接插入 PPT、Word 或 Markdown 报告。

与 `src/server/` 交互式仪表盘**相互独立**，本包可脱离服务器单独使用。

## 模块一览

| 模块 | 功能 |
|------|------|
| `_style.py` | 共享样式：中文字体自适应、指标中文标签、统一配色 |
| `api.py` | 高层入口 `render_all()` / `render_year()`，串联所有绘图函数 |
| `choropleth.py` | 中国地图热力图 + 梯队分布图（Matplotlib 静态渲染 GeoJSON） |
| `radar.py` | 多省多维雷达对比图（指标归一化后正向越大越好） |
| `ranking.py` | 综合得分排名榜（TOP10 / 末位5 / 完整榜） |
| `trend.py` | 多年份得分趋势折线图（单年自动跳过） |

## 使用方式

```bash
# 从项目根目录运行，生成到 output/ 目录
uv run python main.py --viz --year 2024
```

也可在代码中直接调用高层入口：

```python
from src.visualization import render_all, render_year

# 生成单个年份的全部图表
render_all(scores, raw_df, year=2024)

# 或生成多年趋势图（需累积多年的 scores）
render_year(scores, raw_df, year=2024)
```

## 输出格式

所有文件输出到 `output/` 目录：

| 类型 | 文件 | 说明 |
|------|------|------|
| PNG | `map_{year}.png`, `radar_{year}.png`, `rank_{year}.png`, `trend_{year}.png` | 高分辨率位图 |
| HTML | `map_{year}.html`, 等 | 内嵌 base64 PNG 的独立页面 |

## 设计说明

- **Choropleth 用 Matplotlib 而非 Plotly** — 避免浏览器端 WebGL 跨平台兼容问题（如 Linux 下 bdata 解码差异），渲染结果稳定可复现
- 所有字体、配色集中管理在 `_style.py`，确保 PPT 中风格统一
- 每个模块独立可单独调用（见 `__init__.py` 中的低层接口），也可通过 `api.py` 一站式生成
