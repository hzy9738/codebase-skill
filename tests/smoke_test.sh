#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "${ROOT_DIR}/bin/codebase"
bash -n "${ROOT_DIR}/scripts/install.sh"
python3 -m py_compile \
  "${ROOT_DIR}/src/codebase_cli/__init__.py" \
  "${ROOT_DIR}/src/codebase_cli/__main__.py" \
  "${ROOT_DIR}/src/codebase_cli/cli.py"
PYTHONPATH="${ROOT_DIR}/src" python3 -m codebase_cli --help >/dev/null
"${ROOT_DIR}/bin/codebase" --help >/dev/null
PYTHONPATH="${ROOT_DIR}/src" python3 -m unittest discover -s "${ROOT_DIR}/tests" -p "test_*.py"
