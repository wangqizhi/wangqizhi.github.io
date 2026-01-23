#!/usr/bin/env python3
"""
Game translation processing script.
Processes game-trans.json to fill in English and Japanese names.
"""

import json
import re
import sys
from typing import Dict, List, Tuple

def is_english_name(text: str) -> bool:
    """Check if the text is primarily English/Latin characters."""
    if not text:
        return False
    # Count non-ASCII characters
    non_ascii = sum(1 for c in text if ord(c) > 127)
    # If less than 30% non-ASCII, consider it English
    return non_ascii < len(text) * 0.3

def main():
    input_file = '/opt/project/github/wangqizhi/public/data/game-trans.json'
    output_file = '/opt/project/github/wangqizhi/public/data/game-trans-updated.json'

    # Read the file
    print("Reading input file...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    print(f"Total entries: {total}")

    # Process entries that are already English
    english_count = 0
    for entry in data:
        if not entry.get('en') and is_english_name(entry.get('zh', '')):
            entry['en'] = entry['zh']
            entry['jp'] = entry['zh']  # Default to English name
            english_count += 1

    print(f"Auto-filled {english_count} entries with English names")

    # Show sample of what needs manual search
    print("\nEntries needing manual search (first 20):")
    count = 0
    for i, entry in enumerate(data):
        if not entry.get('en'):
            print(f"{i+1}. zh=\"{entry['zh']}\"")
            count += 1
            if count >= 20:
                break

    remaining = sum(1 for e in data if not e.get('en'))
    print(f"\nRemaining entries to process: {remaining}")

    # Write updated file
    print(f"\nWriting to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Done!")

if __name__ == '__main__':
    main()
