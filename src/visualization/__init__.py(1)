"""可视化模块对外接口。

主入口：``render_all(result, raw_df, year)``
    接收 main.py 中 ``analyze()`` 的返回值 + 原始指标 DataFrame，
    一次性生成所有图表到 output/ 目录。

低层接口（也可单独调用）：
    draw_map(scores, clusters, year)
    draw_radar(raw_df, year)
    draw_ranking(scores, year)
    draw_trend(scores_by_year)
"""

from .api import render_all, render_year
from .choropleth import draw_map
from .radar import draw_radar
from .ranking import draw_ranking
from .trend import draw_trend

__all__ = [
    "render_all",
    "render_year",
    "draw_map",
    "draw_radar",
    "draw_ranking",
    "draw_trend",
]
