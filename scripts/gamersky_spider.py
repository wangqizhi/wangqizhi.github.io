#!/usr/bin/env python3
import scrapy
from scrapy.crawler import CrawlerProcess
from datetime import date
import os


class GamerskyReleaseSpider(scrapy.Spider):
    name = "gamersky_release_switch2_202601"
    start_urls = ["https://ku.gamersky.com/release/switch2_202601/"]
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

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, meta={"playwright": True})

    def parse(self, response):
        lis = response.xpath("/html/body/div[7]/div[2]/div[1]/ul/li")
        if not lis:
            self.logger.warning(
                "No items found with XPath; page may be JS-rendered or structure changed."
            )
        for li in lis:
            title = li.xpath("./div[1]/div[2]/a/text()").get()
            href = li.xpath("./div[1]/div[2]/a/@href").get()
            date = li.xpath("./div[1]/div[3]/text()").get()
            genre = li.xpath("./div[1]/div[4]/a/text()").get()
            summary = li.xpath("./div[1]/div[6]/p/text()").get()
            yield {
                "title": title.strip() if title else None,
                "href": response.urljoin(href) if href else None,
                "date": date.strip() if date else None,
                "genre": genre.strip() if genre else None,
                "summary": summary.strip() if summary else None,
            }


def main():
    output_dir = os.path.join("public", "raw-data", "gamesky")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{date.today().strftime('%Y-%m-%d')}.txt"
    output_path = os.path.join(output_dir, filename)

    process = CrawlerProcess(
        settings={
            "FEEDS": {
                output_path: {
                    "format": "json",
                    "encoding": "utf-8",
                }
            }
        }
    )
    process.crawl(GamerskyReleaseSpider)
    process.start()


if __name__ == "__main__":
    main()
