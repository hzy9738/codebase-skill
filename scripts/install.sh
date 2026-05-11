#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-hzy9738}"
REPO_NAME="${REPO_NAME:-codebase-skill}"
REPO_BRANCH="${REPO_BRANCH:-main}"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}"

LOCAL_BIN_DIR="${LOCAL_BIN_DIR:-${HOME}/.local/bin}"
INSTALL_UPSTREAM="${INSTALL_UPSTREAM:-1}"

usage() {
  cat <<'HELPEOF'
Usage:
  curl -fsSL <install-url> | bash
  curl -fsSL <install-url> | bash -s -- [options]

Options:
  --skip-upstream-install   Do not install codebase-memory-mcp during setup
  --help                    Show this help message
HELPEOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-upstream-install) INSTALL_UPSTREAM=0; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) echo "Unsupported platform. Expected macOS or Linux." >&2; exit 1 ;;
esac

ensure_node() {
  if command -v node >/dev/null 2>&1; then
    local ver
    ver="$(node --version | sed 's/^v//; s/\..*//')"
    if [[ "${ver}" -lt 19 ]]; then
      echo "Node.js >= 19 is required (found: $(node --version))." >&2
      exit 1
    fi
    echo "Using: node $(node --version)"
    return 0
  fi
  echo "Node.js >= 19 is not found."
  echo "Install Node.js with: brew install node (macOS) or https://nodejs.org"
  exit 1
}
ensure_node

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."

if [[ -f "${ROOT_DIR}/bin/codebase" ]]; then
  INSTALL_DIR="${ROOT_DIR}"
  echo "==> Installing from local clone: ${INSTALL_DIR}"
else
  echo "==> Downloading ${REPO_URL} (branch: ${REPO_BRANCH}) ..."
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required for remote installation." >&2
    exit 1
  fi
  TMP_DIR="$(mktemp -d)"
  trap "rm -rf '${TMP_DIR}'" EXIT
  curl -fsSL "${REPO_URL}/archive/refs/heads/${REPO_BRANCH}.tar.gz" | tar xz -C "${TMP_DIR}"
  INSTALL_DIR="${TMP_DIR}/${REPO_NAME}-${REPO_BRANCH}"
  echo "==> Extracted to: ${INSTALL_DIR}"
fi

echo "==> Installing codebase CLI to ${LOCAL_BIN_DIR}..."
mkdir -p "${LOCAL_BIN_DIR}"
rm -f "${LOCAL_BIN_DIR}/codebase" 2>/dev/null || true

cp "${INSTALL_DIR}/bin/codebase" "${LOCAL_BIN_DIR}/codebase"
chmod +x "${LOCAL_BIN_DIR}/codebase"
echo "codebase installed at ${LOCAL_BIN_DIR}/codebase"

if [[ ":${PATH}:" != *":${LOCAL_BIN_DIR}:"* ]]; then
  echo "Add ${LOCAL_BIN_DIR} to PATH if needed:"
  echo "  echo 'export PATH="${LOCAL_BIN_DIR}:\$PATH"' >> ~/.bashrc"
fi

if [[ "${INSTALL_UPSTREAM}" == "1" ]] && ! command -v codebase-memory-mcp >/dev/null 2>&1; then
  if command -v curl >/dev/null 2>&1; then
    echo "==> Installing upstream codebase-memory-mcp ..."
    curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config --dir="${LOCAL_BIN_DIR}"
  fi
fi

if ! command -v codebase-memory-mcp >/dev/null 2>&1 && [ ! -x "${LOCAL_BIN_DIR}/codebase-memory-mcp" ]; then
  echo "Warning: codebase-memory-mcp not found."
  echo "Run: codebase install-runtime"
fi

echo "Installed CLI: ${LOCAL_BIN_DIR}/codebase"
echo "Try: codebase --help"
