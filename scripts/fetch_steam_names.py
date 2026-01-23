#!/usr/bin/env python3
"""
从 Steam 获取游戏的英文和日文名称
读取 un-trans-game.json，输出格式：中文|-|英文|-|日文
支持断点续传，每完成一个游戏立即写入文件
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


# 全局速率限制
last_request_time = 0


def rate_limited_request(delay):
    """请求前等待，确保请求间隔"""
    global last_request_time
    now = time.time()
    elapsed = now - last_request_time
    if elapsed < delay:
        time.sleep(delay - elapsed)
    last_request_time = time.time()


def search_steam_game(game_name, delay):
    """通过 Steam 搜索 API 查找游戏，返回 appid"""
    rate_limited_request(delay)
    encoded_name = urllib.parse.quote(game_name)
    url = f"https://store.steampowered.com/api/storesearch/?term={encoded_name}&l=schinese&cc=CN"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("total", 0) > 0:
                return data["items"][0]["id"]
    except Exception as e:
        print(f"  # 搜索失败: {e}")
    return None


def get_game_name_by_language(appid, language, delay):
    """获取指定语言的游戏名称"""
    rate_limited_request(delay)
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l={language}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            app_data = data.get(str(appid), {})
            if app_data.get("success"):
                return app_data["data"].get("name")
    except Exception as e:
        print(f"  # 获取 {language} 名称失败: {e}")
    return None


def process_game(zh_name, delay):
    """处理单个游戏，返回结果字符串"""
    # 搜索游戏获取 appid
    appid = search_steam_game(zh_name, delay)

    if appid:
        en_name = get_game_name_by_language(appid, "english", delay)
        jp_name = get_game_name_by_language(appid, "japanese", delay)
        en_name = en_name or zh_name
        jp_name = jp_name or en_name
    else:
        en_name = zh_name
        jp_name = zh_name

    return f"{zh_name}|-|{en_name}|-|{jp_name}"


def load_progress(progress_path):
    """加载进度文件，返回已完成的游戏集合"""
    completed = set()
    if progress_path.exists():
        with open(progress_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    # 提取中文名（第一个字段）
                    zh_name = line.split("|-|")[0]
                    completed.add(zh_name)
    return completed


def main():
    parser = argparse.ArgumentParser(description="从 Steam 获取游戏的英文和日文名称")
    parser.add_argument(
        "-r", "--rate",
        type=float,
        default=5,
        help="每秒请求数 (默认: 5)"
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default=None,
        help="输入文件路径 (默认: public/data/un-trans-game.json)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出文件路径 (默认: public/data/trans-result.txt)"
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="忽略进度，从头开始"
    )
    args = parser.parse_args()

    # 计算请求间隔
    delay = 1.0 / args.rate

    # 设置路径
    base_path = Path(__file__).parent.parent
    input_path = Path(args.input) if args.input else base_path / "public" / "data" / "un-trans-game.json"
    output_path = Path(args.output) if args.output else base_path / "public" / "data" / "trans-result.txt"

    # 读取游戏列表
    with open(input_path, "r", encoding="utf-8") as f:
        games = [line.strip() for line in f if line.strip()]

    total = len(games)

    # 加载已完成的进度
    if args.restart:
        completed = set()
        # 清空输出文件
        output_path.write_text("", encoding="utf-8")
        print("# 忽略进度，从头开始")
    else:
        completed = load_progress(output_path)

    pending = [g for g in games if g not in completed]

    print(f"# 共 {total} 个游戏")
    print(f"# 已完成: {len(completed)}, 待处理: {len(pending)}")
    print(f"# 请求频率: {args.rate}/s (间隔 {delay:.2f}s)")
    print(f"# 输出文件: {output_path}\n")

    if not pending:
        print("# 所有游戏已处理完成!")
        return

    # 逐个处理，实时写入
    for i, zh_name in enumerate(pending, 1):
        print(f"[{len(completed) + i}/{total}] {zh_name}")

        result = process_game(zh_name, delay)
        print(f"  -> {result}\n")

        # 立即追加写入输出文件
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(result + "\n")

    print(f"# 完成! 结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
