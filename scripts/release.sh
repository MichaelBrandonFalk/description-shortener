#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(tr -d '\n' < VERSION)
archive="downloads/Description-Shortener-V${version}-Apple-Silicon.zip"
test -f "$archive"
test -z "$(git status --porcelain)" || { echo 'Commit source changes before releasing.' >&2; exit 1; }
if git rev-parse "v${version}" >/dev/null 2>&1; then echo 'Version tag already exists. Bump VERSION.' >&2; exit 1; fi
.venv/bin/python -m unittest discover -s tests
codesign --verify --deep --strict "dist/Description Shortener V${version}.app"
git tag -a "v${version}" -m "Release Description Shortener V${version}"
git push origin HEAD "v${version}"
gh release create "v${version}" "$archive" "downloads/SHA256-V${version}.txt" --verify-tag --title "Description Shortener V${version}" --notes-file docs/release_notes.md
