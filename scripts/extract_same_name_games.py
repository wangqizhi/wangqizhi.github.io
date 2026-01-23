#!/usr/bin/env python3
"""
提取 game-trans.json 中 en 字段和 zh 字段相同的所有游戏名
过滤掉纯英文标题，只保留包含中文字符的游戏名
"""

import json
import re
from pathlib import Path


def contains_chinese(text):
    """检查字符串是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def main():
    # 读取 game-trans.json
    json_path = Path(__file__).parent.parent / "public" / "data" / "game-trans.json"

    with open(json_path, "r", encoding="utf-8") as f:
        games = json.load(f)

    # 提取 en 和 zh 相同的游戏，且过滤掉纯英文标题
    same_name_games = []
    for game in games:
        en_name = game.get("en", "")
        zh_name = game.get("zh", "")
        if en_name and zh_name and en_name == zh_name and contains_chinese(zh_name):
            same_name_games.append(en_name)

    # 输出结果
    print(f"共找到 {len(same_name_games)} 个 en 和 zh 字段相同的游戏:\n")
    for name in same_name_games:
        print(name)


if __name__ == "__main__":
    main()
