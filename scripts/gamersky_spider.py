#!/usr/bin/env python3
"""Gamersky 游戏发售时间爬虫

专门爬取 gamersky 网站的游戏发售信息。
"""
import argparse
import os

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy_playwright.page import PageMethod

from spider_base import BaseGameSpider, iter_year_months, parse_date


PLATFORM_LABELS = {
    "pc": "PC",
    "ps5": "PS5",
    "xsx": "Xbox Series X|S",
    "ps4": "PS4",
    "switch": "NS",
    "switch2": "NS2",
    "xboxone": "Xbox One",
}


class GamerskyReleaseSpider(BaseGameSpider):
    """Gamersky 游戏发售信息爬虫"""

    name = "gamersky_release"

    LIST_XPATH = "/html/body/div[7]/div[2]/div[1]/ul/li"
    LIST_SELECTOR = f"xpath={LIST_XPATH}"
    LIST_TIMEOUT_MS = 15000

    def __init__(self, url_configs=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_configs = url_configs or []

    def start_requests(self):
        for url, platform_label in self.url_configs:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "platform_label": platform_label,
                    "playwright_page_methods": [
                        PageMethod(
                            "wait_for_selector",
                            self.LIST_SELECTOR,
                            timeout=self.LIST_TIMEOUT_MS,
                        )
                    ],
                },
                errback=self.errback,
            )

    def parse(self, response):
        lis = response.xpath(self.LIST_XPATH)
        if not lis:
            self.failed_pages.setdefault(
                response.url, "Release list not found after page load."
            )
            self.logger.warning("No items found for %s", response.url)
            return
        platform_label = response.meta.get("platform_label", "Unknown")
        for li in lis:
            title = li.xpath("./div[1]/div[2]/a/text()").get()
            raw_date = li.xpath("./div[1]/div[3]/text()").get()
            genre = li.xpath("./div[1]/div[4]/a/text()").get()
            summary = li.xpath("./div[1]/div[6]/p/text()").get()
            parsed_date = parse_date(raw_date)
            self.add_game(parsed_date, title, genre, summary, platform_label)


def build_urls(platforms, start_ym, end_ym):
    """构建 Gamersky 发售列表 URL"""
    url_configs = []
    for platform in platforms:
        platform_label = PLATFORM_LABELS.get(platform, platform.upper())
        for ym in iter_year_months(start_ym, end_ym):
            url = f"https://ku.gamersky.com/release/{platform}_{ym}/"
            url_configs.append((url, platform_label))
    return url_configs


def parse_args():
    parser = argparse.ArgumentParser(description="Gamersky release crawler")
    parser.add_argument(
        "--platforms",
        default="pc,ps5,xsx,ps4,switch,switch2,xboxone",
        help="Comma-separated: pc,ps5,xsx,ps4,switch,switch2,xboxone",
    )
    parser.add_argument("--start-ym", default="202101", help="Start year+month, e.g. 202101")
    parser.add_argument("--end-ym", default="202603", help="End year+month, e.g. 202603")
    parser.add_argument(
        "--output-dir",
        default=os.path.join("public", "data", "game-release"),
        help="Base output dir for per-year JSON files",
    )
    parser.add_argument(
        "-f", "--force-cover",
        action="store_true",
        help="强制覆盖已存在的数据，不询问用户",
    )
    args = parser.parse_args()
    args.platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    return args


def main():
    args = parse_args()
    process = CrawlerProcess()
    url_configs = build_urls(args.platforms, args.start_ym, args.end_ym)
    process.crawl(
        GamerskyReleaseSpider,
        url_configs=url_configs,
        output_dir=args.output_dir,
        force_cover=args.force_cover,
    )
    process.start()


if __name__ == "__main__":
    main()
