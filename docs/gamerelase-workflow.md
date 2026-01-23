# Game Release Data Workflow

This document describes the standard workflow for scraping and publishing game release JSON data for the site.

## 1) Run the Spider

The `gamersky_spider.py` script handles everything automatically:
- Scrapes game release data from multiple platforms (PC, PS5, Xbox Series X|S, PS4, NS, NS2, Xbox One)
- Organizes data by release date and year
- Generates per-year JSON files (e.g., `2025.json`, `2026.json`)
- **Automatically updates `index.json`** with the list of available year files

### Usage

Basic usage (scrapes all platforms from 2021-01 to 2026-03):

```bash
cd /opt/project/github/wangqizhi
python3 scripts/gamersky_spider.py
```

Custom date range and platforms:

```bash
python3 scripts/gamersky_spider.py \
  --platforms "pc,ps5,switch" \
  --start-ym "202601" \
  --end-ym "202603"
```

### Output Structure

```
public/data/game-release/
├── index.json          # Auto-generated manifest
├── 2021.json          # Games by date for 2021
├── 2022.json
├── 2023.json
├── 2024.json
├── 2025.json
└── 2026.json
```

### Output Format

Each year file contains an array of release dates:

```json
[
  {
    "date": "2026-01-15",
    "displayDate": "2026-01-15",
    "games": [
      {
        "title": "Game Title",
        "genre": ["Action", "RPG"],
        "style": "Description...",
        "platforms": ["NS", "PC", "PS5"]
      }
    ]
  }
]
```

The `index.json` file lists all available year files:

```json
[
  "2021.json",
  "2022.json",
  "2023.json",
  "2024.json",
  "2025.json",
  "2026.json"
]
```

## 2) Verify in the UI

- Start the dev server
- Check the timeline renders the new dates and games correctly
