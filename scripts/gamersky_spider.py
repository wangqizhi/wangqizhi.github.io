#!/usr/bin/env python3
import argparse
import os
import re
from collections import defaultdict
from datetime import date, datetime

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy_playwright.page import PageMethod


class GamerskyReleaseSpider(scrapy.Spider):
    name = "gamersky_release"
    custom_settings = {
        "LOG_LEVEL": "INFO",
        "USER_AGENT": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
    }
    LIST_XPATH = "/html/body/div[7]/div[2]/div[1]/ul/li"
    LIST_SELECTOR = f"xpath={LIST_XPATH}"
    LIST_TIMEOUT_MS = 15000

    def __init__(self, url_configs=None, output_dir=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_configs = url_configs or []
        self.output_dir = output_dir or os.path.join("public", "data", "game-release")
        self.by_date = defaultdict(dict)
        self.failed_pages = {}

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
        for li in lis:
            title = li.xpath("./div[1]/div[2]/a/text()").get()
            raw_date = li.xpath("./div[1]/div[3]/text()").get()
            genre = li.xpath("./div[1]/div[4]/a/text()").get()
            summary = li.xpath("./div[1]/div[6]/p/text()").get()
            parsed_date = parse_date(raw_date)
            if not parsed_date:
                continue
            title_text = title.strip() if title else ""
            if not title_text:
                continue
            platform_label = response.meta.get("platform_label", "Unknown")
            game_key = title_text.lower()
            existing = self.by_date[parsed_date].get(game_key)
            if existing:
                existing["platforms"].add(platform_label)
                if not existing["style"] and summary:
                    existing["style"] = summary.strip()
                if genre:
                    existing["genre"].update(split_genres(genre))
            else:
                self.by_date[parsed_date][game_key] = {
                    "title": title_text,
                    "genre": set(split_genres(genre)),
                    "style": summary.strip() if summary else "",
                    "platforms": {platform_label},
                }

    def closed(self, reason):
        by_year = defaultdict(list)
        for day, games_by_title in sorted(self.by_date.items()):
            year = day.split("-")[0]
            games = [finalize_game(game) for game in games_by_title.values()]
            by_year[year].append(
                {
                    "date": day,
                    "displayDate": day,
                    "games": games,
                }
            )

        os.makedirs(self.output_dir, exist_ok=True)
        for year, groups in sorted(by_year.items()):
            output_path = os.path.join(self.output_dir, f"{year}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_dumps(groups))
        write_index(self.output_dir, sorted(by_year.keys()))

        if self.failed_pages:
            failed = [f"{url} ({reason})" for url, reason in self.failed_pages.items()]
            self.logger.warning("Failed pages:\n%s", "\n".join(failed))

    def errback(self, failure):
        request = failure.request
        reason = getattr(failure.value, "message", repr(failure.value))
        self.failed_pages.setdefault(request.url, reason)
        self.logger.warning("Request failed: %s (%s)", request.url, reason)


def main():
    args = parse_args()
    process = CrawlerProcess()
    url_configs = build_urls(args.platforms, args.start_ym, args.end_ym)
    process.crawl(
        GamerskyReleaseSpider,
        url_configs=url_configs,
        output_dir=args.output_dir,
    )
    process.start()

PLATFORM_LABELS = {
    "pc": "PC",
    "ps5": "PS5",
    "xsx": "Xbox Series X|S",
    "ps4": "PS4",
    "switch": "NS",
    "switch2": "NS2",
    "xboxone": "Xbox One",
}


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
    args = parser.parse_args()
    args.platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    return args


def build_urls(platforms, start_ym, end_ym):
    url_configs = []
    for platform in platforms:
        platform_label = PLATFORM_LABELS.get(platform, platform.upper())
        for ym in iter_year_months(start_ym, end_ym):
            url = f"https://ku.gamersky.com/release/{platform}_{ym}/"
            url_configs.append((url, platform_label))
    return url_configs


def iter_year_months(start_ym, end_ym):
    start_dt = datetime.strptime(start_ym, "%Y%m")
    end_dt = datetime.strptime(end_ym, "%Y%m")
    current = date(start_dt.year, start_dt.month, 1)
    end = date(end_dt.year, end_dt.month, 1)
    while current <= end:
        yield current.strftime("%Y%m")
        year = current.year + (current.month // 12)
        month = 1 if current.month == 12 else current.month + 1
        current = date(year, month, 1)


def parse_date(text):
    if not text:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def split_genres(text):
    if not text:
        return []
    raw = re.split(r"[\/、，,]\s*", text.strip())
    return [item for item in (part.strip() for part in raw) if item]


def finalize_game(game):
    return {
        "title": game["title"],
        "genre": sorted(game["genre"]),
        "style": game["style"],
        "platforms": sorted(game["platforms"]),
    }


def json_dumps(payload):
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_index(output_dir, years):
    import json

    entries = [f"{year}.json" for year in years]
    index_path = os.path.join(output_dir, "index.json")
    existing_entries = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                existing_entries = [item for item in data if isinstance(item, str)]
        except (OSError, json.JSONDecodeError):
            existing_entries = []

    merged = list(set(existing_entries + entries))

    def sort_key(name):
        match = re.match(r"(\d{4})\.json$", name)
        if match:
            return (0, int(match.group(1)))
        return (1, name)

    merged.sort(key=sort_key)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(json_dumps(merged))


if __name__ == "__main__":
    main()
