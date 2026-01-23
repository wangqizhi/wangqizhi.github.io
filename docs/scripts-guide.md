# Scripts 使用指南

本文档描述 `scripts/` 目录下所有脚本的功能和用法。

---

## 目录

- [构建与开发](#构建与开发)
  - [build.sh](#buildsh)
  - [dev-wsl.sh](#dev-wslsh)
- [数据爬取](#数据爬取)
  - [gamersky_spider.py](#gamersky_spiderpy)
  - [extract-gamersky-release.sh](#extract-gamersky-releasesh)
  - [add_game_from_text.py](#add_game_from_textpy)
- [游戏翻译处理](#游戏翻译处理)
  - [extract-game-trans.py](#extract-game-transpy)
  - [fill_game_trans.py](#fill_game_transpy)
  - [fill_trans_from_result.py](#fill_trans_from_resultpy)
  - [process_game_trans.py](#process_game_transpy)
  - [extract_same_name_games.py](#extract_same_name_gamespy)
  - [extract_chinese_titles.py](#extract_chinese_titlespy)
  - [fetch_steam_names.py](#fetch_steam_namespy)
  - [igdb_query.py](#igdb_querypy)

---

## 构建与开发

### build.sh

**功能**: 执行项目构建，并将构建产物复制到根目录。

**用法**:
```bash
./scripts/build.sh
```

**执行流程**:
1. 运行 `npm run build`
2. 检查 `dist/index.html` 是否生成
3. 复制 `dist/index.html` 到根目录
4. 复制 `dist/assets` 和 `dist/data` 到根目录

---

### dev-wsl.sh

**功能**: 在 WSL 环境下启动开发服务器，自动获取宿主机 IP。

**用法**:
```bash
./scripts/dev-wsl.sh

# 自定义端口
PORT=3000 ./scripts/dev-wsl.sh
```

**参数**:
| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `PORT` | 服务端口 | 29393 |

---

## 数据爬取

### gamersky_spider.py

**功能**: 从游民星空网站爬取游戏发售日期数据，支持多平台、多时间范围。

**依赖**:
```bash
pip install scrapy scrapy-playwright
playwright install chromium
```

**用法**:
```bash
# 默认配置（所有平台，2021-01 到 2026-03）
python scripts/gamersky_spider.py

# 指定平台
python scripts/gamersky_spider.py --platforms pc,ps5,switch

# 指定时间范围
python scripts/gamersky_spider.py --start-ym 202401 --end-ym 202412

# 指定输出目录
python scripts/gamersky_spider.py --output-dir ./output
```

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--platforms` | 平台列表（逗号分隔） | `pc,ps5,xsx,ps4,switch,switch2,xboxone` |
| `--start-ym` | 开始年月 | `202101` |
| `--end-ym` | 结束年月 | `202603` |
| `--output-dir` | 输出目录 | `public/data/game-release` |

**支持的平台**:
- `pc` - PC
- `ps5` - PS5
- `ps4` - PS4
- `xsx` - Xbox Series X|S
- `xboxone` - Xbox One
- `switch` - Nintendo Switch
- `switch2` - Nintendo Switch 2

**输出**: 按年份生成 JSON 文件（如 `2024.json`）和 `index.json` 索引文件。

---

### extract-gamersky-release.sh

**功能**: 使用 agent-browser 从游民星空单个页面提取游戏发售数据（TSV 格式）。

**依赖**: 需要安装 `agent-browser` 工具。

**用法**:
```bash
./scripts/extract-gamersky-release.sh
```

**输出**: TSV 格式（标题、发售日期、游戏类型）

---

### add_game_from_text.py

**功能**: 从用户输入的文案中提取游戏信息（调用 Kimi AI），并自动添加到游戏发售数据中。

**依赖**:
```bash
pip install openai
```

**环境变量** (必需):
| 变量 | 说明 |
|------|------|
| `MOONSHOT_API_KEY` | Kimi API 密钥 |

> 获取方式: https://platform.moonshot.cn/

**用法**:
```bash
# 设置环境变量
export MOONSHOT_API_KEY="your-api-key-here"

# 基本用法
python scripts/add_game_from_text.py -m "你的游戏文案"

# 自动确认，不询问用户
python scripts/add_game_from_text.py -m "游戏文案" -y

# 预览模式（只提取信息，不写入文件）
python scripts/add_game_from_text.py -m "游戏文案" --dry-run
```

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-m, --message` | 包含游戏信息的文案（必需） | - |
| `-y, --yes` | 自动确认，不询问用户 | False |
| `--dry-run` | 预览模式，不写入文件 | False |

**示例**:
```bash
python scripts/add_game_from_text.py -m "《黑神话：悟空》将于2026年8月20日发售，这是一款由游戏科学开发的动作角色扮演游戏，支持PC和PS5平台。玩家将扮演天命人，踏上充满神话色彩的西游之旅。"
```

**工作流程**:
1. 检查环境变量 `MOONSHOT_API_KEY` 是否存在
2. 调用 Kimi API 从文案中提取游戏信息（名称、日期、类型、简介、平台）
3. 显示提取结果，询问用户确认
4. 根据发售日期找到对应的年份数据文件
5. 检查游戏是否已存在（防止冲突）
6. 按日期顺序插入游戏数据

**冲突处理**:
- 如果同一日期下已存在同名游戏，脚本会提示冲突并退出
- 用户需手动处理冲突后重试

**输出**: 更新 `public/data/game-release/{year}.json` 文件

---

## 游戏翻译处理

### extract-game-trans.py

**功能**: 从游戏发售数据中提取所有游戏标题，生成翻译模板文件。

**用法**:
```bash
# 默认配置
python scripts/extract-game-trans.py

# 指定输入目录
python scripts/extract-game-trans.py --input-dir ./data/game-release

# 指定输出文件
python scripts/extract-game-trans.py --output ./output/game-trans.json
```

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input-dir` | 游戏数据目录 | `public/data/game-release` |
| `--output` | 输出文件路径 | `public/data/game-trans.json` |

**输出格式**:
```json
[
  {"zh": "游戏名", "en": "", "jp": ""},
  ...
]
```

---

### fill_game_trans.py

**功能**: 使用内置的已知翻译字典填充游戏翻译。

**规则**:
1. 如果 `zh` 是英文（无中文字符），则 `en = jp = zh`
2. 如果 `zh` 在已知翻译字典中，使用字典中的英文名
3. 未知翻译暂时用中文名占位

**用法**:
```bash
python scripts/fill_game_trans.py
```

**输入/输出**: 直接修改 `public/data/game-trans.json`

---

### fill_trans_from_result.py

**功能**: 从 `trans-result.txt` 读取翻译结果，填充到 `game-trans.json` 中。

**用法**:
```bash
# 默认配置（使用默认路径）
python scripts/fill_trans_from_result.py

# 指定输入和目标文件
python scripts/fill_trans_from_result.py -i ./trans-result.txt -t ./game-trans.json

# 输出到新文件（不覆盖原文件）
python scripts/fill_trans_from_result.py -o ./game-trans-filled.json

# 预览模式（只显示统计，不写入文件）
python scripts/fill_trans_from_result.py --dry-run

# 强制覆盖已有翻译，不提示确认
python scripts/fill_trans_from_result.py -f
```

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 翻译结果文件路径 | `public/data/trans-result.txt` |
| `-t, --target` | 目标 JSON 文件路径 | `public/data/game-trans.json` |
| `-o, --output` | 输出文件路径 | 覆盖目标文件 |
| `-f, --force` | 强制覆盖已有翻译，不提示确认 | - |
| `--dry-run` | 预览模式，不写入文件 | - |

**输入格式** (`trans-result.txt`):
```
中文名|-|英文名|-|日文名
```

**输出**: 更新后的 `game-trans.json`，保留原有格式

---

### process_game_trans.py

**功能**: 处理翻译文件，自动填充英文名的游戏条目。

**用法**:
```bash
python scripts/process_game_trans.py
```

**输入**: `public/data/game-trans.json`
**输出**: `public/data/game-trans-updated.json`

---

### extract_same_name_games.py

**功能**: 提取 `game-trans.json` 中 `en` 和 `zh` 字段相同的游戏名，过滤掉纯英文标题。

**用法**:
```bash
python scripts/extract_same_name_games.py
```

**输出**: 打印所有符合条件的游戏名（即需要翻译的中文游戏名）

---

### extract_chinese_titles.py

**功能**: 从指定年份的游戏发售数据中提取所有中文标题的游戏。

**用法**:
```bash
# 提取 2026 年的中文标题游戏
python scripts/extract_chinese_titles.py 2026

# 提取其他年份
python scripts/extract_chinese_titles.py 2025
python scripts/extract_chinese_titles.py 2024
```

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `year` | 年份（对应 `{year}.json` 文件） | 必需 |

**输入**: `public/data/game-release/{year}.json`

**输出**: 打印所有标题包含中文字符的游戏名

**示例输出**:
```
在 2026.json 中共找到 378 个中文标题游戏:

烧尾宴
修真世界
某天成为妹妹
...
```

---

### fetch_steam_names.py

**功能**: 从 Steam API 批量获取游戏的英文和日文名称，支持断点续传。

**用法**:
```bash
# 默认配置（每秒5个请求）
python scripts/fetch_steam_names.py

# 自定义请求频率（每秒2个请求，更保守）
python scripts/fetch_steam_names.py -r 2

# 指定输入输出文件
python scripts/fetch_steam_names.py -i input.txt -o output.txt

# 忽略进度，从头开始
python scripts/fetch_steam_names.py --restart
```

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-r, --rate` | 每秒请求数 | 5 |
| `-i, --input` | 输入文件路径 | `public/data/un-trans-game.json` |
| `-o, --output` | 输出文件路径 | `public/data/trans-result.txt` |
| `--restart` | 忽略进度，从头开始 | - |

**输入格式**: 每行一个游戏名（中文）

**输出格式**:
```
中文名|-|英文名|-|日文名
```

**断点续传**:
- 每完成一个游戏立即写入输出文件
- 下次启动自动读取输出文件，跳过已完成的游戏
- 使用 `--restart` 可忽略进度从头开始

**注意事项**:
- Steam API 有请求频率限制，如遇 429 错误可降低 `-r` 值
- 如果找不到英文名，默认使用中文名；找不到日文名，默认使用英文名

---

### igdb_query.py

**功能**: 从 IGDB API 查询游戏的中英日文名称。

**API 限制**: 4 requests/second（脚本内置速率限制器自动控制）

**依赖**: 无外部依赖，使用 Python 标准库

**环境变量** (必需):
| 变量 | 说明 |
|------|------|
| `IGDB_CLIENT_ID` | Twitch Client ID |
| `IGDB_CLIENT_SECRET` | Twitch Client Secret |

> 获取方式: https://api-docs.igdb.com/#account-creation

**用法**:
```bash
# 设置环境变量
export IGDB_CLIENT_ID="your_client_id"
export IGDB_CLIENT_SECRET="your_client_secret"

# 查询单个游戏
python scripts/igdb_query.py "The Legend of Zelda"

# 批量查询（从文件读取，每行一个游戏名）
python scripts/igdb_query.py -f games.txt

# 输出为 JSON 格式
python scripts/igdb_query.py "Elden Ring" --json

# 格式化 JSON 输出
python scripts/igdb_query.py "Elden Ring" --json --pretty

# 批量查询并输出到文件
python scripts/igdb_query.py -f games.txt -o results.json --json

# 将所有输出打印到标准输出（方便重定向）
python scripts/igdb_query.py "Elden Ring" -v
```

**参数**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `name` | 要查询的游戏名称 | - |
| `-f, --file` | 从文件批量读取游戏名 | - |
| `-o, --output` | 输出文件路径 | - |
| `--json` | 输出 JSON 格式 | False |
| `--pretty` | 格式化 JSON 输出 | False |
| `-v, --verbose` | 将所有输出打印到标准输出 | False |

**输出格式**:

普通模式:
```
[1/1] 查询: Elden Ring
  EN: Elden Ring
  ZH: 艾尔登法环
  JP: エルデンリング
```

JSON 模式:
```json
{
  "query": "Elden Ring",
  "en": "Elden Ring",
  "zh": "艾尔登法环",
  "jp": "エルデンリング",
  "found": true
}
```

**注意事项**:
- IGDB API 限制为 4 requests/second，脚本内置速率限制器自动处理
- 需要先在 Twitch Developer Portal 注册应用获取凭据
- 中日文名称来自 IGDB 的 `alternative_names` 字段，部分游戏可能缺失

---

## 工作流示例

### 完整的游戏翻译工作流

```bash
# 1. 爬取游戏发售数据
python scripts/gamersky_spider.py

# 2. 提取游戏标题生成翻译模板
python scripts/extract-game-trans.py

# 3. 使用已知字典填充翻译
python scripts/fill_game_trans.py

# 4. 提取需要翻译的游戏名（en == zh 且包含中文）
python scripts/extract_same_name_games.py > public/data/un-trans-game.json

# 5. 从 Steam 获取翻译（支持断点续传）
python scripts/fetch_steam_names.py -r 5

# 6. (可选) 使用 IGDB 补充翻译
python scripts/igdb_query.py -f public/data/un-trans-game.json -o igdb-results.json --json
```
