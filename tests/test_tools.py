"""Unit tests for tool functions — no API keys needed."""

import json
from pathlib import Path

import pytest

from src.agent.tools import (
    compare_years,
    get_cluster_members,
    get_province_detail,
    get_ranking,
    get_weights,
    search_knowledge,
    show_chart,
)

# Check if data exists for 2024
DATA_EXISTS = (Path("data/results/2024_pca/scores.csv").exists() and
               Path("data_cache/indicators_2024.csv").exists())


@pytest.mark.skipif(not DATA_EXISTS, reason="No cached data for 2024")
class TestDataTools:
    def test_get_ranking_returns_top10(self):
        result = get_ranking(2024, top_n=10)
        assert "名" in result
        assert "2024" in result

    def test_get_ranking_top0_returns_all(self):
        result = get_ranking(2024, top_n=0)
        lines = [l for l in result.split("\n") if l.startswith(tuple("0123456789"))]
        assert len(lines) >= 25

    def test_get_ranking_bad_year(self):
        result = get_ranking(2010)
        assert "不支持" in result

    def test_get_province_detail_found(self):
        result = get_province_detail("广东省", 2024)
        assert "广东" in result
        assert "GDP" in result or "指标" in result or "排名" in result

    def test_get_province_detail_not_found(self):
        result = get_province_detail("火星省", 2024)
        assert "未找到" in result

    def test_get_cluster_members_all(self):
        result = get_cluster_members(2024)
        assert "第一梯队" in result
        assert "第四梯队" in result

    def test_get_cluster_members_tier0(self):
        result = get_cluster_members(2024, label=0)
        assert "第一梯队" in result

    def test_get_weights(self):
        result = get_weights(2024)
        assert "权重" in result
        assert "GDP" in result

    def test_compare_years(self):
        result = compare_years("广东省")
        assert "广东省" in result
        assert "排名" in result or "---" in result


class TestShowChart:
    def test_returns_marker(self):
        result = show_chart("ranking", 2024)
        assert result.startswith("<!--chart:")

    def test_default_year(self):
        result = show_chart("scoreMap")
        assert "chart:scoreMap:2024" in result

    def test_with_provinces(self):
        result = show_chart("ranking", 2024, ["广东省", "浙江省"])
        assert "chart:ranking:2024" in result


def test_search_knowledge():
    result = search_knowledge("熵权法")
    assert len(result) > 0
    assert "熵" in result or "权" in result
