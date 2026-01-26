#!/usr/bin/env python3
"""
从用户输入的文案中提取游戏信息并添加到游戏发售数据中。

使用方法:
    python scripts/add_game_from_text.py -m "你的游戏文案" [选项]

环境变量:
    MOONSHOT_API_KEY: Kimi API 密钥

示例:
    python scripts/add_game_from_text.py -m "《艾尔登法环》将于2026年3月15日发售，这是一款由FromSoftware开发的动作角色扮演游戏，支持PC和PS5平台。"
    
    # 添加后自动推送到仓库
    python scripts/add_game_from_text.py -m "《黑神话悟空》将于2026年8月20日发售..." --publish
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Kimi API 配置
BASE_URL = "https://api.moonshot.cn/v1"
MODEL = "kimi-k2-turbo-preview"
ENV_KEY_NAME = "MOONSHOT_API_KEY"


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


def call_kimi_api(api_key: str, user_text: str) -> dict | None:
    """调用 Kimi API 提取游戏信息"""
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

    system_prompt = """你是一个专业的游戏信息提取助手。用户会给你一段包含游戏信息的文案，你需要从中提取以下信息并返回 JSON 格式：

1. title: 游戏名称（字符串）
2. date: 发售日期，格式为 "YYYY-MM-DD"（字符串）
3. genre: 游戏类型（字符串数组），常见类型包括：动作游戏、角色扮演、益智游戏、冒险游戏、模拟游戏、策略游戏、射击游戏、体育游戏、竞速游戏、格斗游戏等
4. style: 游戏简介/描述（字符串）
5. platforms: 发售平台（字符串数组），常见平台包括：PC、PS5、PS4、Xbox Series X/S、Xbox One、Switch、iOS、Android 等

请严格按照以下 JSON 格式返回，不要包含任何其他文字：
{
    "title": "游戏名称",
    "date": "YYYY-MM-DD",
    "genre": ["类型1", "类型2"],
    "style": "游戏简介描述",
    "platforms": ["平台1", "平台2"]
}

注意事项：
- 如果某个信息在文案中没有明确提及，请根据上下文合理推断
- 如果发售日期只有月份没有具体日期，默认为该月1号
- 如果发售日期只有年份，默认为该年1月1号
- 游戏类型请使用中文
- 如果文案中包含多个游戏，只提取第一个游戏的信息
- 只返回 JSON，不要有任何解释文字"""

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


def insert_game(data: list, game_info: dict) -> tuple[list, bool, str]:
    """
    将游戏插入到数据中

    返回: (更新后的数据, 是否成功, 消息)
    """
    target_date = game_info["date"]

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
            return data, False, f"游戏《{game_info['title']}》在 {target_date} 已存在，请处理冲突"

        # 添加游戏到已有日期
        date_entry["games"].append(game_entry)
        return data, True, f"已将《{game_info['title']}》添加到 {target_date}"
    else:
        # 创建新的日期条目
        new_entry = {
            "date": target_date,
            "displayDate": target_date,
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

        return data, True, f"已创建新日期 {target_date} 并添加《{game_info['title']}》"


def format_game_info(game_info: dict) -> str:
    """格式化游戏信息用于显示"""
    return f"""
┌─────────────────────────────────────────────────────────────────┐
│ 提取到的游戏信息                                                 │
├─────────────────────────────────────────────────────────────────┤
│ 游戏名称: {game_info['title']:<51} │
│ 发售日期: {game_info['date']:<51} │
│ 游戏类型: {', '.join(game_info['genre']):<51} │
│ 发售平台: {', '.join(game_info['platforms']):<51} │
├─────────────────────────────────────────────────────────────────┤
│ 游戏简介:                                                        │
│ {game_info['style'][:60]:<62} │
└─────────────────────────────────────────────────────────────────┘
"""


def push_to_git(game_title: str) -> bool:
    """推送更改到 Git 仓库
    
    参数:
        game_title: 游戏名称
    
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
            commit_message = f"chore: 添加游戏《{game_title}》"
            
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
  python scripts/add_game_from_text.py -m "新游戏：黑神话悟空，2026年8月20日，动作RPG，PC/PS5"
        """
    )
    parser.add_argument(
        "-m", "--message",
        required=True,
        help="包含游戏信息的文案"
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
        help="添加游戏后自动推送到 Git 仓库"
    )

    args = parser.parse_args()

    # 检查 API 密钥
    api_key = check_api_key()
    if not api_key:
        print_config_guide()
        sys.exit(1)

    print("正在调用 Kimi API 提取游戏信息...")

    # 调用 API 提取信息
    game_info = call_kimi_api(api_key, args.message)

    if not game_info:
        print("错误: 无法从文案中提取游戏信息")
        sys.exit(1)

    # 验证必要字段
    required_fields = ["title", "date", "genre", "style", "platforms"]
    missing_fields = [f for f in required_fields if f not in game_info or not game_info[f]]

    if missing_fields:
        print(f"错误: 提取的信息缺少必要字段: {', '.join(missing_fields)}")
        print(f"提取结果: {json.dumps(game_info, ensure_ascii=False, indent=2)}")
        sys.exit(1)

    # 显示提取的信息
    print(format_game_info(game_info))

    if args.dry_run:
        print("(dry-run 模式，不写入文件)")
        print("\n生成的 JSON 条目:")
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
        confirm = input("\n是否将此游戏添加到数据中? [y/N]: ").strip().lower()
        if confirm not in ["y", "yes"]:
            print("已取消操作")
            sys.exit(0)

    # 获取年份并加载对应数据文件
    year = game_info["date"].split("-")[0]
    data_file = get_data_file_path(year)

    print(f"\n正在读取数据文件: {data_file}")
    data = load_game_data(data_file)

    if not data:
        print(f"警告: 数据文件不存在或为空，将创建新文件")
        data = []

    # 插入游戏
    updated_data, success, message = insert_game(data, game_info)

    if not success:
        print(f"\n⚠️  冲突: {message}")
        print("请手动处理冲突后重试，或使用其他游戏名称")
        sys.exit(1)

    # 保存数据
    save_game_data(data_file, updated_data)
    print(f"\n✅ {message}")
    print(f"数据已保存到: {data_file}")
    
    # 如果指定了 --publish 参数，推送到 Git
    if args.publish:
        print("\n" + "="*67)
        print("执行 Git 推送...")
        print("="*67)
        if push_to_git(game_info["title"]):
            print("\n✅ 游戏信息已成功推送到仓库")
        else:
            print("\n❌ Git 推送失败，请检查您的 Git 配置和网络连接")
            sys.exit(1)


if __name__ == "__main__":
    main()
