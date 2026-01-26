#!/usr/bin/env python3
"""
从指定年份的游戏发布数据中提取所有中文标题的游戏
用法: python extract_chinese_titles.py 2026
      python extract_chinese_titles.py 2026 --start-month 3
      python extract_chinese_titles.py 2026 --start-month 3 --end-month 6
"""

import argparse
import json
import re
from pathlib import Path


def contains_chinese(text):
    """检查字符串是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def parse_args():
    parser = argparse.ArgumentParser(description="从游戏发布数据中提取中文标题游戏")
    parser.add_argument("year", help="年份，如 2026")
    parser.add_argument(
        "--start-month", "-s",
        type=int,
        default=1,
        choices=range(1, 13),
        metavar="MONTH",
        help="起始月份 (1-12)，默认为 1"
    )
    parser.add_argument(
        "--end-month", "-e",
        type=int,
        default=12,
        choices=range(1, 13),
        metavar="MONTH",
        help="结束月份 (1-12)，默认为 12"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    year = args.year
    start_month = args.start_month
    end_month = args.end_month

    if start_month > end_month:
        print(f"错误: 起始月份 ({start_month}) 不能大于结束月份 ({end_month})")
        return

    json_path = Path(__file__).parent.parent / "public" / "data" / "game-release" / f"{year}.json"

    if not json_path.exists():
        print(f"错误: 文件 {json_path} 不存在")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 提取所有包含中文的 title
    chinese_titles = []
    for entry in data:
        date_str = entry.get("date", "")
        if date_str:
            month = int(date_str.split("-")[1])
            if month < start_month or month > end_month:
                continue
        games = entry.get("games", [])
        for game in games:
            title = game.get("title", "")
            if title and contains_chinese(title):
                chinese_titles.append(title)

    # 输出结果
    month_range = f"{start_month}月-{end_month}月" if start_month != 1 or end_month != 12 else "全年"
    print(f"在 {year}.json ({month_range}) 中共找到 {len(chinese_titles)} 个中文标题游戏:\n")
    for title in chinese_titles:
        print(title)


if __name__ == "__main__":
    main()
