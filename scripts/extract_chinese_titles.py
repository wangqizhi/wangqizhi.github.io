#!/usr/bin/env python3
"""
从指定年份的游戏发布数据中提取所有中文标题的游戏
用法: python extract_chinese_titles.py 2026
"""

import json
import re
import sys
from pathlib import Path


def contains_chinese(text):
    """检查字符串是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def main():
    if len(sys.argv) < 2:
        print("用法: python extract_chinese_titles.py <年份>")
        print("示例: python extract_chinese_titles.py 2026")
        sys.exit(1)

    year = sys.argv[1]
    json_path = Path(__file__).parent.parent / "public" / "data" / "game-release" / f"{year}.json"

    if not json_path.exists():
        print(f"错误: 文件 {json_path} 不存在")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 提取所有包含中文的 title
    chinese_titles = []
    for entry in data:
        games = entry.get("games", [])
        for game in games:
            title = game.get("title", "")
            if title and contains_chinese(title):
                chinese_titles.append(title)

    # 输出结果
    print(f"在 {year}.json 中共找到 {len(chinese_titles)} 个中文标题游戏:\n")
    for title in chinese_titles:
        print(title)


if __name__ == "__main__":
    main()
