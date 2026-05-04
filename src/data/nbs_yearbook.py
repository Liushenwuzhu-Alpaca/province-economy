from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests

from src.config import DATA_RAW_DIR


NBS_YEARBOOK_BASE = "https://www.stats.gov.cn/sj/ndsj/{yearbook_year}/"


@dataclass(frozen=True)
class YearbookTable:
    indicator: str
    title_keyword: str
    preferred_code: str | None = None


TABLES = [
    YearbookTable("gdp", "地区生产总值(2023年)", "C03-09"),
    YearbookTable("income", "分地区居民人均可支配收入", "C06-18"),
    YearbookTable("cpi", "分地区居民消费价格分类指数", "C05-05"),
    YearbookTable("unemployment", "分地区城镇登记失业人员", "C04-14"),
    YearbookTable("fixed_invest", "分地区按领域分固定资产投资比上年增长情况", "C10-05"),
    YearbookTable("fiscal_revenue", "分地区一般公共预算收入", "C07-05"),
    YearbookTable("retail", "社会消费品零售总额", "C15-12"),
]


def _tables_for_year(data_year: int) -> list[YearbookTable]:
    if data_year >= 2024:
        return [
            YearbookTable("unemployment", "分地区失业保险情况", "C24-28")
            if table.indicator == "unemployment"
            else table
            for table in TABLES
        ]
    return TABLES


def yearbook_year_for_data_year(data_year: int) -> int:
    # 中国统计年鉴 2024 usually publishes 2023 annual data.
    return data_year + 1


def _request_text(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def find_yearbook_tables(data_year: int = 2023) -> dict[str, str]:
    yearbook_year = yearbook_year_for_data_year(data_year)
    base_url = NBS_YEARBOOK_BASE.format(yearbook_year=yearbook_year)
    left_html = _request_text(urljoin(base_url, "left.htm"))

    links = re.findall(r"<a\s+href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", left_html, flags=re.I | re.S)
    normalized_links = [(href, re.sub(r"<[^>]+>", "", text).strip()) for href, text in links]

    found: dict[str, str] = {}
    for table in _tables_for_year(data_year):
        href = None

        if table.preferred_code:
            code_pattern = f"{table.preferred_code}.jpg".lower()
            href = next((item_href for item_href, _ in normalized_links if code_pattern in item_href.lower()), None)

        if href is None:
            href = next((item_href for item_href, text in normalized_links if table.title_keyword in text), None)

        if href is not None:
            found[table.indicator] = urljoin(base_url, href)

    return found


def download_yearbook_tables(data_year: int = 2023, output_dir: Path | None = None) -> dict[str, Path]:
    target_dir = output_dir or DATA_RAW_DIR / f"yearbook_{data_year}"
    target_dir.mkdir(parents=True, exist_ok=True)

    downloaded: dict[str, Path] = {}
    for indicator, url in find_yearbook_tables(data_year).items():
        suffix = Path(url).suffix or ".jpg"
        path = target_dir / f"{indicator}{suffix}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)
        downloaded[indicator] = path

    return downloaded
