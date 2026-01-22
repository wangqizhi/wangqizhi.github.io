# Game Release Data Workflow

This document describes the standard workflow for scraping, converting, and
publishing game release JSON data for the site.

## 1) Scrape raw data

- Script: `scripts/gamersky_spider.py`
- Output location: `public/raw-data/gamesky/YYYY-MM-DD.txt`
- Notes: the scraper writes JSON to a date-stamped file.

## 2) Convert raw data into release JSON files

Goal format: `docs/game-release-json.md`

Current conversion (manual script):

```
python3 - <<'PY'
import json
import re
from datetime import datetime
from pathlib import Path

raw_path = Path('public/raw-data/gamesky/2026-01-22.txt')
text = raw_path.read_text(encoding='utf-8').strip()
if '][' in text:
    text = text.split('][', 1)[1]
    text = '[' + text

items = json.loads(text)

DATE_RE = re.compile(r'^(\\d{4})-(\\d{2})-(\\d{2})$')
MONTH_RE = re.compile(r'^(\\d{4})年(\\d{1,2})月$')

def normalize_date(raw):
    if not raw:
        return None, None
    raw = raw.strip()
    if raw.startswith('发行日期：'):
        raw = raw.replace('发行日期：', '', 1).strip()
    m = DATE_RE.match(raw)
    if m:
        year, month, day = map(int, m.groups())
        date_str = f\"{year:04d}-{month:02d}-{day:02d}\"
        display = datetime(year, month, day).strftime('%b %d, %Y')
        return date_str, display
    m = MONTH_RE.match(raw)
    if m:
        year, month = map(int, m.groups())
        date_str = f\"{year:04d}-{month:02d}-01\"
        display = datetime(year, month, 1).strftime('%b %Y')
        return date_str, display
    return None, None

groups = {}
for item in items:
    date_str, display = normalize_date(item.get('date'))
    if not date_str:
        continue
    groups.setdefault(date_str, {
        'date': date_str,
        'displayDate': display or date_str,
        'games': [],
    })
    genre = item.get('genre')
    summary = item.get('summary')
    groups[date_str]['games'].append({
        'title': item.get('title') or '',
        'genre': [genre] if genre else [],
        'style': summary or '',
        'studio': '',
        'platforms': ['Switch'],
    })

out_root = Path('public/data/gamerelase')
for date_str, payload in groups.items():
    year, month, day = date_str.split('-')
    out_dir = out_root / year
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f\"{month}{day}-data.json\"
    out_path = out_dir / filename
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')

print('done')
PY
```

## 3) Update release index

The app loads a manifest of all JSON files from:

```
public/data/gamerelase/index.json
```

Regenerate the manifest:

```
python3 - <<'PY'
import json
from pathlib import Path

root = Path('public/data/gamerelase')
files = sorted(p.relative_to(root).as_posix() for p in root.rglob('*-data.json'))
(root / 'index.json').write_text(json.dumps(files, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('updated', root / 'index.json')
PY
```

## 4) Verify in the UI

- Start the dev server.
- Check the timeline renders the new dates.
