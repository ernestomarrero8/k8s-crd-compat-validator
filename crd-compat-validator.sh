#!/usr/bin/env bash
# All contexts by default; Python handles isolated reports and consolidation.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${PYTHON_BIN:-python3.12}" "$script_dir/batch.py" "$@"
