#!/usr/bin/env bash
set -euo pipefail

REPO_API="https://api.github.com/repos/binarylogic/py-madvr-envy/releases/latest"

LATEST_TAG="${1:-}"
if [[ -z "$LATEST_TAG" ]]; then
  LATEST_TAG="$(python3 - <<'PY'
import json
import urllib.request

url = "https://api.github.com/repos/binarylogic/py-madvr-envy/releases/latest"
with urllib.request.urlopen(url, timeout=20) as resp:
    payload = json.load(resp)
print(payload["tag_name"])
PY
)"
fi

if [[ ! "$LATEST_TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Unexpected tag format: $LATEST_TAG" >&2
  exit 1
fi

CURRENT_TAG="$(python3 - <<'PY'
from pathlib import Path
import re

content = Path("custom_components/madvr_envy/manifest.json").read_text()
match = re.search(r"py-madvr-envy\.git@(v\d+\.\d+\.\d+)", content)
if not match:
    raise SystemExit("Could not find current madvr-envy tag in manifest.json")
print(match.group(1))
PY
)"

if [[ "$CURRENT_TAG" == "$LATEST_TAG" ]]; then
  echo "madvr-envy already at latest: $LATEST_TAG"
  exit 0
fi

python3 - "$LATEST_TAG" <<'PY'
from pathlib import Path
import re
import sys

new_tag = sys.argv[1]
files = [
    Path("custom_components/madvr_envy/manifest.json"),
    Path("pyproject.toml"),
    Path("Makefile"),
]
pattern = re.compile(r"(py-madvr-envy\.git@)v\d+\.\d+\.\d+")

for path in files:
    original = path.read_text()
    updated = pattern.sub(rf"\1{new_tag}", original)
    if original == updated:
        raise SystemExit(f"No replacement made in {path}")
    path.write_text(updated)
PY

uv lock

echo "Updated madvr-envy: $CURRENT_TAG -> $LATEST_TAG"
