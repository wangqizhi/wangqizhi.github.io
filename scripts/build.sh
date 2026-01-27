#!/usr/bin/env bash
set -euo pipefail

npm run build

if [ ! -f dist/index.html ]; then
  echo "Build failed: dist/index.html not found" >&2
  exit 1
fi

cp dist/index.html ./index.html
rm -rf ./assets
cp -R dist/assets ./assets
cp -R dist/data ./
echo "Build complete: dist/index.html -> ./index.html and dist/assets -> ./assets"
