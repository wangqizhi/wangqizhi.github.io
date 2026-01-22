#!/usr/bin/env bash
set -euo pipefail

URL="https://ku.gamersky.com/release/switch2_202601/"

agent-browser open "$URL"
agent-browser wait --fn "(() => { const el = document.evaluate('/html/body/div[7]/div[2]/div[1]/ul', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; return !!(el && el.querySelectorAll('li.lx1').length); })()"

raw=$(
  agent-browser eval "$(cat <<'JS'
(() => {
  try {
    const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
    const list = document.evaluate(
      '/html/body/div[7]/div[2]/div[1]/ul',
      document,
      null,
      XPathResult.FIRST_ORDERED_NODE_TYPE,
      null
    ).singleNodeValue;
    if (!list) return 'NOT_FOUND';

    const rows = [];
    for (const li of list.querySelectorAll('li.lx1')) {
      const title = clean(li.querySelector('.PF_1 .tit a')?.textContent || '');

      const txtNodes = [...li.querySelectorAll('.PF_1 .txt')].map((n) =>
        clean(n.textContent || '')
      );
      const dateNode = txtNodes.find((t) => t.startsWith('发行日期：')) || '';
      const typeNode = txtNodes.find((t) => t.startsWith('游戏类型：')) || '';
      const release_date = dateNode.replace('发行日期：', '').trim();
      const genre = typeNode.replace('游戏类型：', '').trim();

      if (title) {
        rows.push([title, release_date, genre].join('\\t'));
      }
    }

    return rows.length ? rows.join('\\n') : '__EMPTY__';
  } catch (e) {
    return `ERROR: ${e && e.message ? e.message : String(e)}`;
  }
})()
JS
)" 2>&1
)

printf "title\trelease_date\tgenre\n"
printf "%s" "$raw" | python3 - <<'PY'
import json
import sys

text = sys.stdin.read().strip()
if not text:
    raise SystemExit("agent-browser returned empty output")

# agent-browser eval returns a JSON string; decode it.
start = text.find('"')
end = text.rfind('"')
if start == -1 or end == -1 or end <= start:
    raise SystemExit("could not find eval result string")

decoded = json.loads(text[start : end + 1])
if decoded == "NOT_FOUND":
    raise SystemExit("list not found: /html/body/div[7]/div[2]/div[1]/ul")
if decoded.startswith("ERROR:"):
    raise SystemExit(decoded)
if decoded == "__EMPTY__":
    raise SystemExit("no items found in list")
if decoded:
    print(decoded)
PY

agent-browser close
