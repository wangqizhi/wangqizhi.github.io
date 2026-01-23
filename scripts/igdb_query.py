#!/usr/bin/env python3
"""
IGDB 游戏名称查询工具

从 IGDB API 查询游戏的中英日文名称。
API 限制: 4 requests/second

使用前需要设置环境变量:
- IGDB_CLIENT_ID: Twitch Client ID
- IGDB_CLIENT_SECRET: Twitch Client Secret

获取方式: https://api-docs.igdb.com/#account-creation
"""

import argparse
import json
import os
import sys
import time
from typing import Optional
import urllib.request
import urllib.error
import urllib.parse


class RateLimiter:
    """速率限制器，确保不超过指定的请求频率"""

    def __init__(self, max_requests_per_second: float = 4.0):
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0.0

    def wait(self):
        """等待直到可以发送下一个请求"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()


class IGDBClient:
    """IGDB API 客户端"""

    TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"
    IGDB_API_URL = "https://api.igdb.com/v4"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.rate_limiter = RateLimiter(max_requests_per_second=4.0)

    def authenticate(self) -> bool:
        """获取 Twitch OAuth access token"""
        params = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        })

        try:
            req = urllib.request.Request(
                f"{self.TWITCH_AUTH_URL}?{params}",
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.access_token = data.get("access_token")
                return self.access_token is not None
        except urllib.error.URLError as e:
            print(f"认证失败: {e}", file=sys.stderr)
            return False

    def _request(self, endpoint: str, body: str) -> Optional[list]:
        """发送 IGDB API 请求"""
        if not self.access_token:
            print("未认证，请先调用 authenticate()", file=sys.stderr)
            return None

        self.rate_limiter.wait()

        url = f"{self.IGDB_API_URL}/{endpoint}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "text/plain"
        }

        try:
            req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"API 请求失败 ({e.code}): {e.read().decode('utf-8')}", file=sys.stderr)
            return None
        except urllib.error.URLError as e:
            print(f"网络错误: {e}", file=sys.stderr)
            return None

    def search_game(self, name: str, limit: int = 5) -> Optional[list]:
        """搜索游戏"""
        escaped_name = name.replace('"', '\\"')
        body = f'''
            search "{escaped_name}";
            fields name, alternative_names.name, alternative_names.comment;
            limit {limit};
        '''
        return self._request("games", body)

    def get_game_names(self, name: str) -> dict:
        """
        查询游戏的中英日文名称

        返回格式:
        {
            "query": "查询名称",
            "en": "英文名",
            "zh": "中文名",
            "jp": "日文名",
            "found": True/False
        }
        """
        result = {
            "query": name,
            "en": "",
            "zh": "",
            "jp": "",
            "found": False
        }

        games = self.search_game(name)
        if not games or len(games) == 0:
            return result

        game = games[0]
        result["found"] = True
        result["en"] = game.get("name", "")

        alt_names = game.get("alternative_names", [])
        for alt in alt_names:
            comment = (alt.get("comment") or "").lower()
            alt_name = alt.get("name", "")

            if not alt_name:
                continue

            if "chinese" in comment or "简体" in comment or "繁体" in comment or "中文" in comment:
                if not result["zh"]:
                    result["zh"] = alt_name
            elif "japanese" in comment or "日本" in comment or "日文" in comment:
                if not result["jp"]:
                    result["jp"] = alt_name

        return result


def main():
    parser = argparse.ArgumentParser(
        description="从 IGDB 查询游戏的中英日文名称",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查询单个游戏
  python scripts/igdb_query.py "The Legend of Zelda"

  # 批量查询（从文件读取）
  python scripts/igdb_query.py -f games.txt

  # 输出为 JSON 格式
  python scripts/igdb_query.py "Elden Ring" --json

  # 批量查询并输出到文件
  python scripts/igdb_query.py -f games.txt -o results.json --json

  # 将所有输出打印到标准输出（方便重定向）
  python scripts/igdb_query.py "Elden Ring" -v

环境变量:
  IGDB_CLIENT_ID      Twitch Client ID (必需)
  IGDB_CLIENT_SECRET  Twitch Client Secret (必需)

  获取方式: https://api-docs.igdb.com/#account-creation
"""
    )

    parser.add_argument("name", nargs="?", help="要查询的游戏名称")
    parser.add_argument("-f", "--file", help="从文件批量读取游戏名（每行一个）")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--pretty", action="store_true", help="格式化 JSON 输出")
    parser.add_argument("-v", "--verbose", action="store_true", help="将查询结果打印到标准输出")

    args = parser.parse_args()

    if not args.name and not args.file:
        parser.error("请提供游戏名称或使用 -f 指定输入文件")

    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("错误: 请设置环境变量 IGDB_CLIENT_ID 和 IGDB_CLIENT_SECRET", file=sys.stderr)
        print("获取方式: https://api-docs.igdb.com/#account-creation", file=sys.stderr)
        sys.exit(1)

    client = IGDBClient(client_id, client_secret)

    log_out = sys.stdout if args.verbose else sys.stderr
    print("正在认证...", file=log_out)
    if not client.authenticate():
        print("认证失败，请检查 Client ID 和 Secret", file=sys.stderr)
        sys.exit(1)
    print("认证成功", file=log_out)

    games_to_query = []
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            games_to_query = [line.strip() for line in f if line.strip()]
    else:
        games_to_query = [args.name]

    results = []
    total = len(games_to_query)

    for i, game_name in enumerate(games_to_query, 1):
        print(f"[{i}/{total}] 查询: {game_name}", file=log_out)
        result = client.get_game_names(game_name)
        results.append(result)

        if not args.json and not args.output:
            if result["found"]:
                print(f"  EN: {result['en']}")
                print(f"  ZH: {result['zh'] or '(未找到)'}")
                print(f"  JP: {result['jp'] or '(未找到)'}")
            else:
                print(f"  未找到匹配结果")
            print()

    if args.json or args.output:
        output_data = results if len(results) > 1 else results[0]
        if args.pretty:
            json_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        else:
            json_str = json.dumps(output_data, ensure_ascii=False)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"结果已保存到: {args.output}", file=log_out)
        else:
            print(json_str)

    found_count = sum(1 for r in results if r["found"])
    print(f"\n完成: {found_count}/{total} 个游戏查询成功", file=log_out)


if __name__ == "__main__":
    main()
