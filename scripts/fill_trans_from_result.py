#!/usr/bin/env python3
"""
从 trans-result.txt 填充翻译结果到 game-trans.json

trans-result.txt 格式: 中文名|-|英文名|-|日文名
game-trans.json 格式: [{"zh": "...", "en": "...", "jp": "..."}, ...]
"""

import argparse
import json
from pathlib import Path


def load_trans_result(file_path: str) -> dict[str, tuple[str, str]]:
    """
    加载 trans-result.txt 文件，返回字典 {zh: (en, jp)}
    """
    trans_dict = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|-|")
            if len(parts) != 3:
                print(f"警告: 第 {line_num} 行格式错误，跳过: {line[:50]}...")
                continue
            zh, en, jp = parts
            trans_dict[zh] = (en, jp)
    return trans_dict


def fill_game_trans(game_trans: list[dict], trans_dict: dict[str, tuple[str, str]], force: bool = False) -> tuple[int, int]:
    """
    使用翻译字典填充 game-trans 列表，返回 (更新数量, 跳过数量)
    """
    updated_count = 0
    skipped_count = 0
    for item in game_trans:
        zh = item.get("zh", "")
        if zh in trans_dict:
            new_en, new_jp = trans_dict[zh]
            old_en = item.get("en", "")
            old_jp = item.get("jp", "")

            # 检查是否有变化
            if old_en != new_en or old_jp != new_jp:
                # 检查原文件中 zh、en、jp 是否已经不同（说明已有翻译）
                has_existing_trans = (zh != old_en or zh != old_jp)

                if has_existing_trans and not force:
                    # 已有翻译，询问用户确认
                    print(f"\n发现已有翻译:")
                    print(f"  中文: {zh}")
                    print(f"  原 en: {old_en}")
                    print(f"  原 jp: {old_jp}")
                    print(f"  新 en: {new_en}")
                    print(f"  新 jp: {new_jp}")
                    confirm = input("是否覆盖? (y/n, 默认n): ").strip().lower()
                    if confirm != 'y':
                        skipped_count += 1
                        print("  -> 已跳过")
                        continue

                item["en"] = new_en
                item["jp"] = new_jp
                updated_count += 1
    return updated_count, skipped_count


def main():
    parser = argparse.ArgumentParser(
        description="从 trans-result.txt 填充翻译结果到 game-trans.json"
    )
    parser.add_argument(
        "-i", "--input",
        default="public/data/trans-result.txt",
        help="翻译结果文件路径 (默认: public/data/trans-result.txt)"
    )
    parser.add_argument(
        "-t", "--target",
        default="public/data/game-trans.json",
        help="目标 JSON 文件路径 (默认: public/data/game-trans.json)"
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径 (默认: 覆盖目标文件)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示统计信息，不写入文件"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="强制覆盖已有翻译，不提示确认"
    )
    args = parser.parse_args()

    # 解析路径
    input_path = Path(args.input)
    target_path = Path(args.target)
    output_path = Path(args.output) if args.output else target_path

    # 检查文件是否存在
    if not input_path.exists():
        print(f"错误: 翻译结果文件不存在: {input_path}")
        return 1
    if not target_path.exists():
        print(f"错误: 目标 JSON 文件不存在: {target_path}")
        return 1

    # 加载翻译结果
    print(f"加载翻译结果: {input_path}")
    trans_dict = load_trans_result(input_path)
    print(f"  已加载 {len(trans_dict)} 条翻译记录")

    # 加载目标 JSON
    print(f"加载目标文件: {target_path}")
    with open(target_path, "r", encoding="utf-8") as f:
        game_trans = json.load(f)
    print(f"  已加载 {len(game_trans)} 条游戏记录")

    # 填充翻译
    updated_count, skipped_count = fill_game_trans(game_trans, trans_dict, args.force)
    print(f"\n统计:")
    print(f"  匹配并更新: {updated_count} 条")
    print(f"  用户跳过: {skipped_count} 条")

    # 写入文件
    if args.dry_run:
        print("\n[dry-run] 未写入文件")
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(game_trans, f, ensure_ascii=False, indent=2)
        print(f"\n已保存到: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
