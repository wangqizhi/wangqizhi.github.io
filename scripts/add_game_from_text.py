#!/usr/bin/env python3
"""
从用户输入的文案中提取游戏信息并添加到游戏发售数据中。
支持一次从文案中提取并添加多个游戏。

使用方法:
    python scripts/add_game_from_text.py -m "你的游戏文案" [选项]
    python scripts/add_game_from_text.py -f 文案文件.txt [选项]
    cat 文案文件.txt | python scripts/add_game_from_text.py -f - [选项]

环境变量:
    MOONSHOT_API_KEY: Kimi API 密钥

示例:
    # 提取单个游戏
    python scripts/add_game_from_text.py -m "《艾尔登法环》将于2026年3月15日发售，这是一款由FromSoftware开发的动作角色扮演游戏，支持PC和PS5平台。"

    # 一次提取多个游戏
    python scripts/add_game_from_text.py -m "《游戏A》3月发售，动作游戏，PC平台。《游戏B》5月发售，RPG，PS5平台。"

    # 添加后执行编译并推送到仓库
    python scripts/add_game_from_text.py -m "《黑神话悟空》将于2026年8月20日发售..." -b
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from shutil import copy2
from pathlib import Path

# Kimi API 配置
BASE_URL = "https://api.moonshot.cn/v1"
MODEL = "kimi-k2-turbo-preview"
ENV_KEY_NAME = "MOONSHOT_API_KEY"


# 模糊日期关键词 → (排序用编码, 显示用后缀)
# 编码设计：字符串排序中 H > 1, Q > H, T > Q
# 排序结果：具体日期 → 上半年 → 下半年 → 春季 → 夏季 → 秋季 → 冬季 → 年内
VAGUE_DATE_MAP = {
    "春季": ("Q1", "春季"),
    "夏季": ("Q2", "夏季"),
    "秋季": ("Q3", "秋季"),
    "冬季": ("Q4", "冬季"),
    "上半年": ("H1", "上半年"),
    "下半年": ("H2", "下半年"),
    "年内": ("TBD", "年内"),
}


PLATFORM_ALIASES = {
    "pc": "PC",
    "windows": "PC",
    "steam": "PC",
    "ns": "NS",
    "switch": "NS",
    "nintendoswitch": "NS",
    "switch1": "NS",
    "ns2": "NS2",
    "switch2": "NS2",
    "nintendoswitch2": "NS2",
    "ps4": "PS4",
    "playstation4": "PS4",
    "ps5": "PS5",
    "playstation5": "PS5",
    "xboxone": "Xbox One",
    "xbox1": "Xbox One",
    "xb1": "Xbox One",
    "xboxseriesx|s": "Xbox Series X|S",
    "xboxseriesx/s": "Xbox Series X|S",
    "xboxseriesxs": "Xbox Series X|S",
    "xsx": "Xbox Series X|S",
    "ios": "iOS",
    "iphone": "iOS",
    "ipad": "iOS",
    "android": "Android",
}


def parse_game_date(raw_date: str) -> tuple[str, str]:
    """
    解析 AI 返回的日期字段，支持精确日期和模糊日期。

    返回: (排序用date, 显示用displayDate)

    精确日期示例: "2026-03-15" → ("2026-03-15", "2026-03-15")
    模糊日期示例: "2026-春季"  → ("2026-Q1", "2026 春季")
    """
    # 精确日期：YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_date):
        return raw_date, raw_date

    # 模糊日期：尝试匹配关键词
    for keyword, (code, label) in VAGUE_DATE_MAP.items():
        if keyword in raw_date:
            year_match = re.match(r"(\d{4})", raw_date)
            if year_match:
                year = year_match.group(1)
                return f"{year}-{code}", f"{year} {label}"

    # 兜底：仅有年份时视为"年内"
    year_match = re.match(r"^(\d{4})$", raw_date.strip())
    if year_match:
        year = year_match.group(1)
        return f"{year}-TBD", f"{year} 年内"

    # 无法识别，原样返回
    return raw_date, raw_date


def normalize_platform_name(platform: str) -> str:
    """将平台名称规范化到项目使用的写法。"""
    if not isinstance(platform, str):
        return str(platform)

    compact = re.sub(r"[\s\-_]+", "", platform.strip().lower())
    compact = compact.replace("／", "/")
    return PLATFORM_ALIASES.get(compact, platform.strip())


def normalize_platforms(platforms: list) -> list[str]:
    """规范化平台列表并去重（保持顺序）。"""
    normalized: list[str] = []
    for platform in platforms:
        canonical = normalize_platform_name(platform)
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    return normalized


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


def call_kimi_api(api_key: str, user_text: str) -> list[dict] | None:
    """调用 Kimi API 提取游戏信息，支持一次提取多个游戏"""
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

    today = date.today().isoformat()

    system_prompt = """你是一个专业的游戏信息提取助手。用户会给你一段包含游戏信息的文案，你需要从中提取所有游戏的以下信息并返回 JSON 数组格式：

每个游戏包含以下字段：
1. title: 游戏名称（字符串）
2. date: 发售日期，格式为 "YYYY-MM-DD"（字符串）
3. genre: 游戏类型（字符串数组），常见类型包括：动作游戏、角色扮演、益智游戏、冒险游戏、模拟游戏、策略游戏、射击游戏、体育游戏、竞速游戏、格斗游戏等
4. style: 游戏简介/描述（字符串）
5. platforms: 发售平台（字符串数组），请使用规范平台名：PC、NS、NS2、PS5、PS4、Xbox Series X|S、Xbox One、iOS、Android 等

请严格按照以下 JSON 数组格式返回，不要包含任何其他文字：
[
    {{
        "title": "游戏名称",
        "date": "YYYY-MM-DD",
        "genre": ["类型1", "类型2"],
        "style": "游戏简介描述",
        "platforms": ["平台1", "平台2"]
    }}
]

注意事项：
- 如果某个信息在文案中没有明确提及，请根据上下文合理推断
- 如果发售日期只有月份没有具体日期，默认为该月1号
- 如果发售日期是模糊的时间段（如"年内"、"春季"、"秋季"等），请使用 "YYYY-关键词" 格式，例如：
  - "2026年春季" → "2026-春季"
  - "2026年秋季" → "2026-秋季"
  - "2026年内" → "2026-年内"
  - "2026年夏季" → "2026-夏季"
  - "2026年冬季" → "2026-冬季"
  - "2026年上半年" → "2026-上半年"
  - "2026年下半年" → "2026-下半年"
- 如果发售日期只有年份且没有其他时间线索，使用 "YYYY-年内" 格式（如 "2026-年内"）
- 游戏类型请使用中文
- 平台名称请尽量输出规范值：NS（不要写 Switch）、NS2（不要写 Switch 2）
- 提取文案中包含的所有游戏信息，每个游戏作为数组中的一个元素
- 只返回 JSON 数组，不要有任何解释文字

当前系统日期：{today}""".format(today=today)

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

        parsed = json.loads(result_text)

        # 兼容处理：如果 API 返回的是单个对象而非数组，包装为数组
        if isinstance(parsed, dict):
            parsed = [parsed]

        return parsed

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
    return project_root / "public" / "data" / "game-release" / f"{year}.json"


def load_game_data(file_path: Path) -> list:
    """加载游戏数据"""
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_game_data(file_path: Path, data: list):
    """保存游戏数据"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def copy_public_data_to_data(public_file_path: Path) -> Path:
    """将 public 下的 JSON 同步到 data 目录"""
    if not public_file_path.exists():
        raise FileNotFoundError(f"public 数据文件不存在: {public_file_path}")

    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    relative_path = public_file_path.relative_to(project_root / "public")
    target_path = data_dir / relative_path

    target_path.parent.mkdir(parents=True, exist_ok=True)
    copy2(public_file_path, target_path)
    return target_path


def find_date_entry(data: list, target_date: str) -> dict | None:
    """在数据中查找指定日期的条目"""
    for entry in data:
        if entry.get("date") == target_date:
            return entry
    return None


def check_game_exists(games: list, title: str) -> bool:
    """检查游戏是否已存在"""
    for game in games:
        if game.get("title") == title:
            return True
    return False


def insert_game(data: list, game_info: dict, display_date: str | None = None) -> tuple[list, bool, str]:
    """
    将游戏插入到数据中

    参数:
        data: 当前数据列表
        game_info: 游戏信息（含 date 字段为排序用日期）
        display_date: 显示用日期，为 None 时使用 game_info["date"]

    返回: (更新后的数据, 是否成功, 消息)
    """
    target_date = game_info["date"]
    show_date = display_date or target_date

    # 构建游戏条目
    game_entry = {
        "title": game_info["title"],
        "genre": game_info["genre"],
        "style": game_info["style"],
        "platforms": game_info["platforms"]
    }

    # 查找是否存在该日期
    date_entry = find_date_entry(data, target_date)

    if date_entry:
        # 检查游戏是否已存在
        if check_game_exists(date_entry["games"], game_info["title"]):
            return data, False, f"游戏《{game_info['title']}》在 {show_date} 已存在，请处理冲突"

        # 添加游戏到已有日期
        date_entry["games"].append(game_entry)
        return data, True, f"已将《{game_info['title']}》添加到 {show_date}"
    else:
        # 创建新的日期条目
        new_entry = {
            "date": target_date,
            "displayDate": show_date,
            "games": [game_entry]
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

        return data, True, f"已创建新日期 {show_date} 并添加《{game_info['title']}》"


def format_game_info(game_info: dict) -> str:
    """格式化游戏信息用于显示"""
    display_date = game_info.get("_display_date", game_info["date"])
    return f"""
┌─────────────────────────────────────────────────────────────────┐
│ 提取到的游戏信息                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 游戏名称: {game_info['title']:<51} │
│ 发售日期: {display_date:<51} │
│ 游戏类型: {', '.join(game_info['genre']):<51} │
│ 发售平台: {', '.join(game_info['platforms']):<51} │
├─────────────────────────────────────────────────────────────────┤
│ 游戏简介:                                                        │
│ {game_info['style'][:60]:<62} │
└─────────────────────────────────────────────────────────────────┘
"""


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


def push_to_git(game_titles: str) -> bool:
    """推送更改到 Git 仓库

    参数:
        game_titles: 游戏名称（可包含多个，如 "《游戏A》、《游戏B》"）

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
            commit_message = f"chore: 添加游戏{game_titles}"
            
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
        description="从文案中提取游戏信息并添加到游戏发售数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/add_game_from_text.py -m "《艾尔登法环》将于2026年3月15日发售..."
  python scripts/add_game_from_text.py -m "《游戏A》3月发售，PC。《游戏B》5月发售，PS5。"
  python scripts/add_game_from_text.py -f games.txt
        """
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-m", "--message",
        help="包含游戏信息的文案"
    )
    group.add_argument(
        "-f", "--file",
        help="从文件读取游戏文案（支持文本文件路径，使用 - 表示从标准输入读取）"
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
        help="添加游戏后执行编译并推送到 Git 仓库"
    )

    args = parser.parse_args()

    # 获取输入文案：-m 直接传入，-f 从文件读取
    if args.message:
        user_text = args.message
    else:
        file_path = args.file
        try:
            if file_path == "-":
                user_text = sys.stdin.read()
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    user_text = f.read()
        except FileNotFoundError:
            print(f"错误: 文件不存在: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"错误: 读取文件失败 - {e}")
            sys.exit(1)

    if not user_text.strip():
        print("错误: 输入文案为空")
        sys.exit(1)

    # 检查 API 密钥
    api_key = check_api_key()
    if not api_key:
        print_config_guide()
        sys.exit(1)

    print("正在调用 Kimi API 提取游戏信息...")

    # 调用 API 提取信息
    games_info = call_kimi_api(api_key, user_text)

    if not games_info:
        print("错误: 无法从文案中提取游戏信息")
        sys.exit(1)

    print(f"\n共提取到 {len(games_info)} 个游戏信息")

    # 验证每个游戏的必要字段
    required_fields = ["title", "date", "genre", "style", "platforms"]
    valid_games = []

    for i, game_info in enumerate(games_info):
        missing_fields = [f for f in required_fields if f not in game_info or not game_info[f]]

        if missing_fields:
            print(f"\n⚠️  第 {i + 1} 个游戏缺少必要字段: {', '.join(missing_fields)}")
            print(f"提取结果: {json.dumps(game_info, ensure_ascii=False, indent=2)}")
            print("已跳过该游戏")
        else:
            valid_games.append(game_info)

    if not valid_games:
        print("错误: 没有有效的游戏信息可以添加")
        sys.exit(1)

    # 解析日期（支持模糊日期），将解析结果存入 game_info
    for game_info in valid_games:
        sort_date, display_date = parse_game_date(game_info["date"])
        game_info["date"] = sort_date
        game_info["_display_date"] = display_date
        game_info["platforms"] = normalize_platforms(game_info["platforms"])

    # 显示提取的信息
    for i, game_info in enumerate(valid_games):
        print(f"\n--- 游戏 {i + 1}/{len(valid_games)} ---")
        print(format_game_info(game_info))

    if args.dry_run:
        print("(dry-run 模式，不写入文件)")
        print("\n生成的 JSON 条目:")
        for game_info in valid_games:
            entry = {
                "title": game_info["title"],
                "genre": game_info["genre"],
                "style": game_info["style"],
                "platforms": game_info["platforms"]
            }
            print(json.dumps(entry, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 确认是否添加
    if not args.yes:
        game_titles = "、".join(f"《{g['title']}》" for g in valid_games)
        confirm = input(f"\n是否将以上 {len(valid_games)} 个游戏添加到数据中? ({game_titles}) [y/N]: ").strip().lower()
        if confirm not in ["y", "yes"]:
            print("已取消操作")
            sys.exit(0)

    # 按年份分组处理游戏
    games_by_year: dict[str, list[dict]] = {}
    for game_info in valid_games:
        year = game_info["date"].split("-")[0]
        games_by_year.setdefault(year, []).append(game_info)

    added_titles = []
    affected_data_files = []

    for year, games in games_by_year.items():
        data_file = get_data_file_path(year)
        print(f"\n正在读取数据文件: {data_file}")
        data = load_game_data(data_file)

        if not data:
            print(f"警告: 数据文件不存在或为空，将创建新文件")
            data = []

        for game_info in games:
            updated_data, success, message = insert_game(data, game_info, game_info.get("_display_date"))

            if not success:
                print(f"\n⚠️  冲突: {message}")
            else:
                data = updated_data
                added_titles.append(game_info["title"])
                print(f"\n✅ {message}")

        # 保存数据
        save_game_data(data_file, data)
        print(f"数据已保存到: {data_file}")
        affected_data_files.append(data_file)

    if not added_titles:
        print("\n没有成功添加任何游戏")
        sys.exit(1)

    print(f"\n共成功添加 {len(added_titles)} 个游戏")

    # 如果指定了 --publish 参数，同步 public 到 data，编译并推送到 Git
    if args.publish:
        for data_file in affected_data_files:
            try:
                synced_path = copy_public_data_to_data(data_file)
                print(f"已同步到数据目录: {synced_path}")
            except Exception as e:
                print(f"错误: 同步 public 数据到 data 失败 - {e}")
                sys.exit(1)

        print("\n" + "="*67)
        print("执行编译...")
        print("="*67)

        if not run_build():
            print("\n❌ 编译失败，已中止推送")
            sys.exit(1)

        print("\n" + "="*67)
        print("执行 Git 推送...")
        print("="*67)
        commit_title = "、".join(f"《{t}》" for t in added_titles)
        if push_to_git(commit_title):
            print("\n✅ 游戏信息已成功推送到仓库")
        else:
            print("\n❌ Git 推送失败，请检查您的 Git 配置和网络连接")
            sys.exit(1)


if __name__ == "__main__":
    main()
