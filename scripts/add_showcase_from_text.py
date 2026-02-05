#!/usr/bin/env python3
"""
从用户输入的文案中提取展示会/发布会信息并添加到数据中。

使用方法:
    python scripts/add_showcase_from_text.py -m "你的发布会文案" [选项]

环境变量:
    MOONSHOT_API_KEY: Kimi API 密钥

示例:
    python scripts/add_showcase_from_text.py -m "暴雪展示会官宣！《魔兽世界》——1月30日凌晨1：00"

    # 添加后执行编译并推送到仓库
    python scripts/add_showcase_from_text.py -m "任天堂直面会将于2月20日晚上10点播出..." -b
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Kimi API 配置
BASE_URL = "https://api.moonshot.cn/v1"
MODEL = "kimi-k2-turbo-preview"
ENV_KEY_NAME = "MOONSHOT_API_KEY"

# 当前年份，用于日期推断
CURRENT_YEAR = datetime.now().year


def check_api_key() -> str | None:
    """检查环境变量中是否存在 API 密钥"""
    return os.environ.get(ENV_KEY_NAME)


def print_config_guide():
    """打印 API 密钥配置指南"""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    缺少 API 密钥配置                              ║
╠══════════════════════════════════════════════════════════════════╣
║  请设置环境变量 {ENV_KEY_NAME}                            ║
║                                                                  ║
║  配置方法:                                                       ║
║                                                                  ║
║  Linux/macOS (临时):                                             ║
║    export {ENV_KEY_NAME}="your-api-key-here"              ║
║                                                                  ║
║  Linux/macOS (永久 - 添加到 ~/.bashrc 或 ~/.zshrc):              ║
║    echo 'export {ENV_KEY_NAME}="your-api-key-here"' >> ~/.bashrc ║
║    source ~/.bashrc                                              ║
║                                                                  ║
║  Windows (CMD):                                                  ║
║    set {ENV_KEY_NAME}=your-api-key-here                   ║
║                                                                  ║
║  Windows (PowerShell):                                           ║
║    $env:{ENV_KEY_NAME}="your-api-key-here"                ║
║                                                                  ║
║  获取 API 密钥: https://platform.moonshot.cn/                    ║
╚══════════════════════════════════════════════════════════════════╝
""")


def call_kimi_api(api_key: str, user_text: str) -> list | None:
    """调用 Kimi API 提取展示会信息"""
    try:
        from openai import OpenAI
    except ImportError:
        print("错误: 请先安装 openai 库")
        print("运行: pip install openai")
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
    )

    system_prompt = f"""你是一个专业的游戏活动信息提取助手。用户会给你一段包含游戏展示会/发布会信息的文案，你需要从中提取信息并返回 JSON 格式。

当前年份是 {CURRENT_YEAR}。如果文案中的日期没有指定年份，请根据上下文推断：
- 如果文案提到"本月"、"本周"等，使用 {CURRENT_YEAR} 年
- 如果月份已经过去（比如现在是3月，但文案提到1月），考虑是 {CURRENT_YEAR + 1} 年
- 如果不确定，默认使用 {CURRENT_YEAR} 年

需要提取的信息（返回一个 JSON 数组，每个元素对应一场展示会）：

1. title: 展示会名称（字符串），格式建议："主办方 + 展示会/发布会/直面会"，如果是某个游戏的专题展示，可以包含游戏名
2. title_en: 展示会名称的英文翻译（字符串）
3. date: 展示会日期时间，格式为 "YYYY-MM-DD HH:mm"（字符串），使用24小时制
4. genre: 固定为 ["showcase"]（字符串数组）
5. style: 相关游戏或活动简介（字符串），列出将会展示的游戏名称，或者活动的简要描述
6. style_en: style 字段的英文翻译（字符串）

请严格按照以下 JSON 数组格式返回，不要包含任何其他文字：
[
  {{
    "title": "展示会名称",
    "title_en": "Showcase Name in English",
    "date": "YYYY-MM-DD HH:mm",
    "genre": ["showcase"],
    "style": "相关游戏或简介",
    "style_en": "Related games or description in English"
  }}
]

注意事项：
- 如果文案中包含多个不同时间的展示会，请分别提取为数组中的不同元素
- 将中国时区的"凌晨"理解为 00:00-06:00，"早上"为 06:00-09:00
- 时间请转换为24小时制
- 如果只有日期没有具体时间，默认为该日 00:00
- 只返回 JSON 数组，不要有任何解释文字
- title_en 和 style_en 必须是准确的英文翻译，游戏名称使用官方英文名"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.3,
        )

        result_text = response.choices[0].message.content.strip()

        # 尝试清理可能的 markdown 代码块
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            # 移除首尾的 ``` 行
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            result_text = "\n".join(lines)

        return json.loads(result_text)

    except json.JSONDecodeError as e:
        print(f"错误: API 返回的内容无法解析为 JSON")
        print(f"原始返回: {result_text}")
        print(f"解析错误: {e}")
        return None
    except Exception as e:
        print(f"错误: 调用 Kimi API 失败 - {e}")
        return None


def get_data_file_path(year: str) -> Path:
    """获取数据文件路径"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    return project_root / "public" / "data" / "showcase" / f"{year}.json"


def load_showcase_data(file_path: Path) -> list:
    """加载展示会数据"""
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_showcase_data(file_path: Path, data: list):
    """保存展示会数据"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_date_entry(data: list, target_date: str) -> dict | None:
    """在数据中查找指定日期的条目（只比较日期部分）"""
    # 提取日期部分（YYYY-MM-DD）
    date_only = target_date.split(" ")[0]
    for entry in data:
        if entry.get("date", "").split(" ")[0] == date_only:
            return entry
    return None


def check_showcase_exists(showcases: list, title: str, time: str) -> bool:
    """检查展示会是否已存在（同时匹配标题和时间）"""
    for showcase in showcases:
        if showcase.get("title") == title:
            # 如果标题相同，还需检查时间是否相同
            return True
    return False


def insert_showcase(data: list, showcase_info: dict) -> tuple[list, bool, str]:
    """
    将展示会插入到数据中

    返回: (更新后的数据, 是否成功, 消息)
    """
    target_datetime = showcase_info["date"]
    target_date = target_datetime.split(" ")[0]  # 提取日期部分

    # 构建展示会条目（每个 showcase 独立包含 displayDate）
    showcase_entry = {
        "title": showcase_info["title"],
        "title_en": showcase_info["title_en"],
        "displayDate": target_datetime,
        "genre": showcase_info["genre"],
        "style": showcase_info["style"],
        "style_en": showcase_info["style_en"],
    }

    # 查找是否存在该日期
    date_entry = find_date_entry(data, target_datetime)

    if date_entry:
        # 检查展示会是否已存在
        if check_showcase_exists(date_entry["showcases"], showcase_info["title"], target_datetime):
            return data, False, f"展示会《{showcase_info['title']}》在 {target_datetime} 已存在，请处理冲突"

        # 添加展示会到已有日期
        date_entry["showcases"].append(showcase_entry)
        return data, True, f"已将《{showcase_info['title']}》添加到 {target_date}"
    else:
        # 创建新的日期条目（不再需要 group 级别的 displayDate）
        new_entry = {
            "date": target_date,
            "showcases": [showcase_entry]
        }

        # 按日期排序插入
        inserted = False
        for i, entry in enumerate(data):
            if entry["date"] > target_date:
                data.insert(i, new_entry)
                inserted = True
                break

        if not inserted:
            data.append(new_entry)

        return data, True, f"已创建新日期 {target_datetime} 并添加《{showcase_info['title']}》"


def format_showcase_info(showcase_info: dict) -> str:
    """格式化展示会信息用于显示"""
    return f"""
┌─────────────────────────────────────────────────────────────────┐
│ 提取到的展示会信息                                               │
├─────────────────────────────────────────────────────────────────┤
│ 展示会名称: {showcase_info['title']:<49} │
│ 展示时间:   {showcase_info['date']:<49} │
│ 类型:       {', '.join(showcase_info['genre']):<49} │
├─────────────────────────────────────────────────────────────────┤
│ 相关内容/简介:                                                   │
│ {showcase_info['style'][:60]:<62} │
└─────────────────────────────────────────────────────────────────┘
"""


def format_all_showcases(showcases: list) -> str:
    """格式化所有展示会信息用于显示"""
    result = f"\n共提取到 {len(showcases)} 个展示会:\n"
    for i, showcase in enumerate(showcases, 1):
        result += f"\n{'='*67}\n"
        result += f"【{i}】{showcase['title']}\n"
        result += f"    英文: {showcase['title_en']}\n"
        result += f"    时间: {showcase['date']}\n"
        result += f"    类型: {', '.join(showcase['genre'])}\n"
        result += f"    简介: {showcase['style']}\n"
        result += f"    英文简介: {showcase['style_en']}\n"
    result += f"\n{'='*67}\n"
    return result


def run_build() -> bool:
    """执行 build.sh 编译脚本

    返回:
        成功返回 True，失败返回 False
    """
    try:
        script_dir = Path(__file__).parent
        build_script = script_dir / "build.sh"

        if not build_script.exists():
            print(f"错误: 找不到编译脚本 {build_script}")
            return False

        print(f"\n执行编译脚本: {build_script}")
        result = subprocess.run(
            ["bash", str(build_script)],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            print(f"错误: 编译失败")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False

        print("✅ 编译成功")
        if result.stdout:
            print(result.stdout)
        return True

    except Exception as e:
        print(f"错误: 执行编译脚本失败 - {e}")
        return False


def push_to_git(showcase_title: str) -> bool:
    """推送更改到 Git 仓库

    参数:
        showcase_title: 展示会名称

    返回:
        成功返回 True，失败返回 False
    """
    try:
        # 获取项目根目录
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        # 保存当前工作目录
        original_cwd = os.getcwd()

        try:
            # 切换到项目根目录
            os.chdir(project_root)

            # 执行 git add
            print("\n执行 git add...")
            result = subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"错误: git add 失败")
                print(f"STDERR: {result.stderr}")
                return False

            # 创建 commit 消息
            commit_message = f"chore: 添加展示会《{showcase_title}》"

            # 执行 git commit
            print(f"执行 git commit: {commit_message}")
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                # 如果没有更改，也算成功
                if "nothing to commit" in result.stdout or "no changes added to commit" in result.stdout:
                    print("⚠️  没有更改可提交")
                    return True
                print(f"错误: git commit 失败")
                print(f"STDERR: {result.stderr}")
                return False

            print("✅ git commit 成功")

            # 执行 git push
            print("执行 git push...")
            result = subprocess.run(
                ["git", "push"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"错误: git push 失败")
                print(f"STDERR: {result.stderr}")
                return False

            print("✅ git push 成功")
            return True

        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)

    except Exception as e:
        print(f"错误: Git 操作失败 - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="从文案中提取展示会/发布会信息并添加到数据中",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/add_showcase_from_text.py -m "暴雪展示会官宣！《魔兽世界》——1月30日凌晨1：00"
  python scripts/add_showcase_from_text.py -m "任天堂直面会将于2月20日晚上10点播出，将公布多款新游戏信息"
        """
    )
    parser.add_argument(
        "-m", "--message",
        required=True,
        help="包含展示会信息的文案"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="自动确认，不询问用户"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅提取信息，不实际写入文件"
    )
    parser.add_argument(
        "-b", "--publish",
        action="store_true",
        help="添加展示会后执行编译并推送到 Git 仓库"
    )

    args = parser.parse_args()

    # 检查 API 密钥
    api_key = check_api_key()
    if not api_key:
        print_config_guide()
        sys.exit(1)

    print("正在调用 Kimi API 提取展示会信息...")

    # 调用 API 提取信息
    showcases = call_kimi_api(api_key, args.message)

    if not showcases:
        print("错误: 无法从文案中提取展示会信息")
        sys.exit(1)

    # 确保返回的是列表
    if isinstance(showcases, dict):
        showcases = [showcases]

    # 验证必要字段
    required_fields = ["title", "title_en", "date", "genre", "style", "style_en"]
    for showcase in showcases:
        missing_fields = [f for f in required_fields if f not in showcase or not showcase[f]]
        if missing_fields:
            print(f"错误: 提取的信息缺少必要字段: {', '.join(missing_fields)}")
            print(f"提取结果: {json.dumps(showcase, ensure_ascii=False, indent=2)}")
            sys.exit(1)

    # 显示提取的信息
    print(format_all_showcases(showcases))

    if args.dry_run:
        print("(dry-run 模式，不写入文件)")
        print("\n生成的 JSON 条目:")
        for showcase in showcases:
            entry = {
                "title": showcase["title"],
                "title_en": showcase["title_en"],
                "displayDate": showcase["date"],
                "genre": showcase["genre"],
                "style": showcase["style"],
                "style_en": showcase["style_en"],
            }
            print(json.dumps(entry, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 确认是否添加
    if not args.yes:
        confirm = input("\n是否将这些展示会添加到数据中? [y/N]: ").strip().lower()
        if confirm not in ["y", "yes"]:
            print("已取消操作")
            sys.exit(0)

    # 按年份分组处理
    success_count = 0
    fail_count = 0
    last_title = ""

    for showcase in showcases:
        # 获取年份并加载对应数据文件
        year = showcase["date"].split("-")[0]
        data_file = get_data_file_path(year)

        print(f"\n正在读取数据文件: {data_file}")
        data = load_showcase_data(data_file)

        if not data:
            print(f"警告: 数据文件不存在或为空，将创建新文件")
            data = []

        # 插入展示会
        updated_data, success, message = insert_showcase(data, showcase)

        if not success:
            print(f"\n⚠️  冲突: {message}")
            fail_count += 1
        else:
            # 保存数据
            save_showcase_data(data_file, updated_data)
            print(f"\n✅ {message}")
            print(f"数据已保存到: {data_file}")
            success_count += 1
            last_title = showcase["title"]

    # 打印总结
    print(f"\n{'='*67}")
    print(f"处理完成: 成功 {success_count} 个，失败 {fail_count} 个")
    print(f"{'='*67}")

    # 如果指定了 --publish 参数，编译并推送到 Git
    if args.publish and success_count > 0:
        print("\n" + "="*67)
        print("执行编译...")
        print("="*67)

        if not run_build():
            print("\n❌ 编译失败，已中止推送")
            sys.exit(1)

        print("\n" + "="*67)
        print("执行 Git 推送...")
        print("="*67)

        commit_title = last_title if success_count == 1 else f"{success_count}个展示会"
        if push_to_git(commit_title):
            print("\n✅ 展示会信息已成功推送到仓库")
        else:
            print("\n❌ Git 推送失败，请检查您的 Git 配置和网络连接")
            sys.exit(1)


if __name__ == "__main__":
    main()
