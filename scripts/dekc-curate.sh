#!/usr/bin/env bash
# Post-edit curation for DEKC knowledge bundles.
# Reads tool payload from stdin (Claude/Grok PostToolUse); no-ops outside a bundle.
set -euo pipefail

ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PAYLOAD="$(cat || true)"

# Extract a file path from common JSON shapes
FILE=""
if command -v python3 >/dev/null 2>&1; then
  FILE="$(printf '%s' "$PAYLOAD" | python3 -c '
import json,sys
raw=sys.stdin.read().strip()
if not raw:
  raise SystemExit(0)
try:
  d=json.loads(raw)
except Exception:
  raise SystemExit(0)
for key in ("file_path","path","filePath"):
  if isinstance(d.get(key), str):
    print(d[key]); raise SystemExit(0)
tool = d.get("tool_input") or d.get("input") or {}
if isinstance(tool, dict):
  for key in ("file_path","path","filePath"):
    if isinstance(tool.get(key), str):
      print(tool[key]); raise SystemExit(0)
' 2>/dev/null || true)"
fi

if [[ -z "${FILE}" ]]; then
  exit 0
fi

# Walk up for OKF/DEKC bundle (index.md with okf_version or dekc tags)
DIR="$(dirname "$FILE")"
BUNDLE=""
for _ in 1 2 3 4 5 6 7 8; do
  if [[ -f "$DIR/index.md" ]] && grep -qE 'okf_version|dekc' "$DIR/index.md" 2>/dev/null; then
    BUNDLE="$DIR"
    break
  fi
  if [[ -d "$DIR/.okf" ]]; then
    BUNDLE="$DIR/.okf"
    break
  fi
  PARENT="$(dirname "$DIR")"
  [[ "$PARENT" == "$DIR" ]] && break
  DIR="$PARENT"
done

if [[ -z "$BUNDLE" ]]; then
  exit 0
fi

# Only curate markdown under the bundle
case "$FILE" in
  *.md) ;;
  *) exit 0 ;;
esac

python3 "$ROOT/scripts/dekc_validate.py" --bundle "$BUNDLE" >/tmp/dekc-curate-validate.txt 2>&1 || true
# Refresh indexes lightly when catalog files change
# Refresh only the catalog containing the edited file. Refreshing all 32 on
# every edit is a whole-file read-modify-write per catalog, so rapid edits raced
# by construction -- and it did far more work than the change required.
python3 - <<PY
from pathlib import Path
import sys
sys.path.insert(0, "${ROOT}/scripts")
from dekc_common import refresh_catalog_index, CATALOGS
bundle = Path("${BUNDLE}")
edited = Path("${FILE}")
try:
    catalog = edited.resolve().relative_to(bundle.resolve()).parts[0]
except (ValueError, IndexError):
    catalog = None
if catalog in CATALOGS and (bundle / catalog).is_dir():
    refresh_catalog_index(bundle, catalog)
    print("dekc-curate: refreshed", catalog, "for", bundle)
PY

exit 0
