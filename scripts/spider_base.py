#!/usr/bin/env python3
"""爬虫基础设施模块

提供爬虫通用的工具函数和基类，包括：
- JSON 文件操作
- 日期处理
- 数据标准化
- Scrapy 基础配置
"""
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime

import scrapy


# ============== Scrapy 基础配置 ==============

DEFAULT_SPIDER_SETTINGS = {
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


class BaseGameSpider(scrapy.Spider):
    """游戏信息爬虫基类"""

    custom_settings = DEFAULT_SPIDER_SETTINGS.copy()

    def __init__(self, output_dir=None, force_cover=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_dir = output_dir or os.path.join("public", "data", "game-release")
        self.force_cover = force_cover
        self.by_date = defaultdict(dict)
        self.failed_pages = {}

    def add_game(self, parsed_date, title, genre, summary, platform_label):
        """添加或更新游戏数据"""
        if not parsed_date or not title:
            return
        title_text = title.strip()
        if not title_text:
            return
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
        """爬虫关闭时输出数据到 JSON 文件"""
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
            if self.force_cover:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(json_dumps(groups))
            else:
                merged_groups = merge_with_existing(
                    output_path, groups, self.logger
                )
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(json_dumps(merged_groups))
        write_index(self.output_dir, sorted(by_year.keys()))

        if self.failed_pages:
            failed = [f"{url} ({reason})" for url, reason in self.failed_pages.items()]
            self.logger.warning("Failed pages:\n%s", "\n".join(failed))

    def errback(self, failure):
        """请求失败回调"""
        request = failure.request
        reason = getattr(failure.value, "message", repr(failure.value))
        self.failed_pages.setdefault(request.url, reason)
        self.logger.warning("Request failed: %s (%s)", request.url, reason)


# ============== 日期处理 ==============


def iter_year_months(start_ym, end_ym):
    """迭代指定范围内的年月（格式：YYYYMM）"""
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
    """从文本中解析日期（格式：YYYY-MM-DD）"""
    if not text:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


# ============== 游戏翻译映射 ==============

# 默认翻译文件路径
DEFAULT_TRANS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "game-trans.json"
)

# 全局缓存
_game_title_map = None


def load_game_trans(trans_path=None):
    """
    加载游戏翻译映射，建立从任意语言名称到所有语言名称集合的映射
    返回: {title_lower: {all_titles_lower}}
    """
    global _game_title_map
    if _game_title_map is not None:
        return _game_title_map

    trans_path = trans_path or DEFAULT_TRANS_PATH
    _game_title_map = {}

    if not os.path.exists(trans_path):
        return _game_title_map

    try:
        with open(trans_path, "r", encoding="utf-8") as f:
            trans_list = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _game_title_map

    for entry in trans_list:
        titles = set()
        for lang in ("zh", "en", "jp"):
            title = entry.get(lang, "").strip()
            if title:
                titles.add(title.lower())
        for title in titles:
            _game_title_map[title] = titles

    return _game_title_map


def get_all_title_variants(title):
    """获取游戏名的所有语言版本（小写）"""
    title_map = load_game_trans()
    title_lower = title.lower()
    return title_map.get(title_lower, {title_lower})


def titles_match(title1, title2):
    """检查两个游戏名是否是同一个游戏（考虑多语言）"""
    t1_lower = title1.lower()
    t2_lower = title2.lower()
    if t1_lower == t2_lower:
        return True
    variants = get_all_title_variants(t1_lower)
    return t2_lower in variants


# ============== 数据处理 ==============


def split_genres(text):
    """分割游戏类型字符串"""
    if not text:
        return []
    raw = re.split(r"[\/、，,]\s*", text.strip())
    return [item for item in (part.strip() for part in raw) if item]


def finalize_game(game):
    """标准化游戏数据结构"""
    return {
        "title": game["title"],
        "genre": sorted(game["genre"]),
        "style": game["style"],
        "platforms": sorted(game["platforms"]),
    }


# ============== JSON 文件操作 ==============


def load_existing_json(filepath):
    """加载现有的 JSON 文件"""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def ask_user_choice(game_title, date_str):
    """询问用户如何处理冲突的游戏"""
    print(f"\n发现冲突: [{date_str}] {game_title}")
    print("  [c] 覆盖 (cover)")
    print("  [s] 跳过 (skip)")
    print("  [a] 全部覆盖 (all cover)")
    print("  [n] 全部跳过 (all skip)")
    while True:
        choice = input("请选择 [c/s/a/n]: ").strip().lower()
        if choice in ("c", "s", "a", "n"):
            return choice
        print("无效输入，请重新选择")


def find_matching_old_game(new_title, old_games_by_title):
    """在旧游戏列表中查找匹配的游戏（考虑多语言）"""
    new_lower = new_title.lower()
    # 先精确匹配
    if new_lower in old_games_by_title:
        return old_games_by_title[new_lower]
    # 再通过翻译映射匹配
    new_variants = get_all_title_variants(new_lower)
    for old_title, old_game in old_games_by_title.items():
        if old_title in new_variants:
            return old_game
    return None


def merge_with_existing(filepath, new_groups, logger):
    """合并新数据与现有 JSON 文件，遇到冲突时询问用户"""
    existing_groups = load_existing_json(filepath)
    if not existing_groups:
        return new_groups

    existing_by_date = {g["date"]: g for g in existing_groups}
    all_cover = False
    all_skip = False
    result = []
    processed_dates = set()

    for new_group in new_groups:
        date_str = new_group["date"]
        processed_dates.add(date_str)

        if date_str not in existing_by_date:
            result.append(new_group)
            continue

        old_group = existing_by_date[date_str]
        old_games_by_title = {g["title"].lower(): g for g in old_group.get("games", [])}
        merged_games = []
        matched_old_titles = set()

        for new_game in new_group.get("games", []):
            old_game = find_matching_old_game(new_game["title"], old_games_by_title)

            if old_game is None:
                merged_games.append(new_game)
                continue

            matched_old_titles.add(old_game["title"].lower())

            if all_cover:
                merged_games.append(new_game)
                continue
            if all_skip:
                merged_games.append(old_game)
                continue

            # 显示新旧游戏名便于用户判断
            if new_game["title"].lower() != old_game["title"].lower():
                print(f"\n发现冲突: [{date_str}]")
                print(f"  新: {new_game['title']}")
                print(f"  旧: {old_game['title']}")
                print("  （翻译映射匹配）")
            else:
                print(f"\n发现冲突: [{date_str}] {new_game['title']}")
            print("  [c] 覆盖 (cover)")
            print("  [s] 跳过 (skip)")
            print("  [a] 全部覆盖 (all cover)")
            print("  [n] 全部跳过 (all skip)")

            while True:
                choice = input("请选择 [c/s/a/n]: ").strip().lower()
                if choice in ("c", "s", "a", "n"):
                    break
                print("无效输入，请重新选择")

            if choice == "c":
                merged_games.append(new_game)
            elif choice == "s":
                merged_games.append(old_game)
            elif choice == "a":
                all_cover = True
                merged_games.append(new_game)
            elif choice == "n":
                all_skip = True
                merged_games.append(old_game)

        # 添加未匹配的旧游戏
        for old_game in old_group.get("games", []):
            if old_game["title"].lower() not in matched_old_titles:
                merged_games.append(old_game)

        result.append({
            "date": date_str,
            "displayDate": new_group.get("displayDate", date_str),
            "games": merged_games,
        })

    for old_group in existing_groups:
        if old_group["date"] not in processed_dates:
            result.append(old_group)

    result.sort(key=lambda x: x["date"])
    return result


def json_dumps(payload):
    """序列化为 JSON 字符串"""
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_index(output_dir, years):
    """写入或更新索引文件"""
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
