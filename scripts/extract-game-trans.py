#!/usr/bin/env python3
import argparse
import json
import os
import re


DEFAULT_INPUT_DIR = os.path.join("public", "data", "game-release")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract game titles into a translation template file."
    )
    parser.add_argument(
        "--input-dir",
        default=DEFAULT_INPUT_DIR,
        help="Input directory containing game-release JSON files",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (defaults to sibling of input dir)",
    )
    return parser.parse_args()


def normalize_title(title):
    return re.sub(r"\s+", " ", title).strip()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def list_source_files(input_dir):
    index_path = os.path.join(input_dir, "index.json")
    if os.path.exists(index_path):
        data = read_json(index_path)
        if isinstance(data, list):
            files = []
            for item in data:
                if not isinstance(item, str) or not item.endswith(".json"):
                    continue
                files.append(os.path.join(input_dir, item))
            return files
    files = []
    for name in sorted(os.listdir(input_dir)):
        if not name.endswith(".json") or name == "index.json":
            continue
        files.append(os.path.join(input_dir, name))
    return files


def iter_titles(data):
    if not isinstance(data, list):
        return
    for entry in data:
        if not isinstance(entry, dict):
            continue
        games = entry.get("games")
        if not isinstance(games, list):
            continue
        for game in games:
            if not isinstance(game, dict):
                continue
            title = game.get("title")
            if not isinstance(title, str):
                continue
            clean = normalize_title(title)
            if clean:
                yield clean


def main():
    args = parse_args()
    input_dir = args.input_dir
    if not os.path.isdir(input_dir):
        raise SystemExit(f"Input dir not found: {input_dir}")

    output_path = args.output or os.path.join(
        os.path.dirname(os.path.normpath(input_dir)),
        "game-trans.json",
    )
    files = list_source_files(input_dir)
    if not files:
        raise SystemExit(f"No source JSON files found in {input_dir}")

    seen = set()
    titles = []
    for path in files:
        if not os.path.exists(path):
            continue
        data = read_json(path)
        for title in iter_titles(data):
            if title in seen:
                continue
            seen.add(title)
            titles.append(title)

    entries = [{"zh": title, "en": "", "jp": ""} for title in titles]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Wrote {len(entries)} titles to {output_path}")


if __name__ == "__main__":
    main()
