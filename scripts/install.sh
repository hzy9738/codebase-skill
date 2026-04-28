#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-hzy9738}"
REPO_NAME="${REPO_NAME:-codebase-skill}"
REPO_BRANCH="${REPO_BRANCH:-main}"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}"

LOCAL_BIN_DIR="${LOCAL_BIN_DIR:-${HOME}/.local/bin}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_UPSTREAM="${INSTALL_UPSTREAM:-1}"

usage() {
  cat <<'EOF'
Usage:
  curl -fsSL <install-url> | bash
  curl -fsSL <install-url> | bash -s -- [options]

Options:
  --skip-upstream-install   Do not install codebase-memory-mcp during setup
  --python <path>           Python executable to use
  --help                    Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-upstream-install)
      INSTALL_UPSTREAM=0
      shift
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$(uname -s)" in
  Darwin|Linux) ;;
  *)
    echo "Unsupported platform. Expected macOS or Linux." >&2
    exit 1
    ;;
esac

ensure_python() {
  local want_bin="$1"
  local os_name
  os_name="$(uname -s)"

  if command -v "${want_bin}" >/dev/null 2>&1; then
    return 0
  fi

  echo "Python (${want_bin}) is not found."
  echo

  if [[ "${os_name}" == "Darwin" ]]; then
    echo "  Install: brew install python"
    read -r -p "Run this command now? [Y/n] " confirm || true
    if [[ ! "${confirm:-y}" =~ ^[Nn] ]]; then
      if command -v brew >/dev/null 2>&1; then
        brew install python || {
          echo "brew install python failed." >&2
          exit 1
        }
      else
        echo "Homebrew not found. Install it first: https://brew.sh" >&2
        exit 1
      fi
    else
      echo "Please install Python and re-run the installer." >&2
      exit 1
    fi
  elif [[ "${os_name}" == "Linux" ]]; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "  Install: sudo apt-get update && sudo apt-get install -y python3 python3-pip"
      read -r -p "Run this command now? [Y/n] " confirm || true
      if [[ ! "${confirm:-y}" =~ ^[Nn] ]]; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip || {
          echo "apt-get install failed." >&2
          exit 1
        }
      else
        echo "Please install Python and re-run the installer." >&2
        exit 1
      fi
    else
      echo "Unsupported Linux package manager. Please install python3 manually." >&2
      exit 1
    fi
  fi

  if ! command -v "${want_bin}" >/dev/null 2>&1; then
    echo "Python installation seems to have failed. Check and re-run." >&2
    exit 1
  fi
}

ensure_python "${PYTHON_BIN}"

if ! "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1; then
  "${PYTHON_BIN}" -m ensurepip --upgrade --user >/dev/null 2>&1 || {
    echo "python pip is unavailable and ensurepip failed" >&2
    exit 1
  }
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."

if [[ -f "${ROOT_DIR}/pyproject.toml" ]] && [[ -f "${ROOT_DIR}/src/codebase_cli/cli.py" ]]; then
  INSTALL_DIR="${ROOT_DIR}"
  echo "==> Installing from local clone: ${INSTALL_DIR}"
else
  echo "==> Downloading ${REPO_URL} (branch: ${REPO_BRANCH}) ..."
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required for remote installation. Install curl first." >&2
    exit 1
  fi
  TMP_DIR="$(mktemp -d)"
  trap "rm -rf '${TMP_DIR}'" EXIT
  TARBALL_URL="${REPO_URL}/archive/refs/heads/${REPO_BRANCH}.tar.gz"
  curl -fsSL "${TARBALL_URL}" | tar xz -C "${TMP_DIR}"
  INSTALL_DIR="${TMP_DIR}/${REPO_NAME}-${REPO_BRANCH}"
  echo "==> Extracted to: ${INSTALL_DIR}"
fi

pip_install_repo() {
  local pip_log
  pip_log="$(mktemp)"

  if "${PYTHON_BIN}" -m pip install --user --upgrade "${INSTALL_DIR}" >"${pip_log}" 2>&1; then
    rm -f "${pip_log}"
    return 0
  fi

  if "${PYTHON_BIN}" -m pip help install 2>/dev/null | grep -q -- "--break-system-packages" && \
     grep -q "externally-managed-environment" "${pip_log}"; then
    rm -f "${pip_log}"
    "${PYTHON_BIN}" -m pip install --user --break-system-packages --upgrade "${INSTALL_DIR}"
    return 0
  fi

  cat "${pip_log}" >&2
  rm -f "${pip_log}"
  return 1
}

mkdir -p "${LOCAL_BIN_DIR}"
if ! pip_install_repo; then
  echo "Failed to install the package with pip." >&2
  exit 1
fi

if [[ ":${PATH}:" != *":${LOCAL_BIN_DIR}:"* ]]; then
  echo
  echo "Add ${LOCAL_BIN_DIR} to PATH if needed:"
  echo "  echo 'export PATH=\"${LOCAL_BIN_DIR}:\$PATH\"' >> ~/.bashrc"
fi

if [[ "${INSTALL_UPSTREAM}" == "1" ]] && \
   ! command -v codebase-memory-mcp >/dev/null 2>&1; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "Skipping codebase-memory-mcp install because curl is unavailable." >&2
    echo "Run \`codebase install-runtime\` later after curl/proxy is ready." >&2
  else
    echo "==> Installing upstream codebase-memory-mcp ..."
    curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | \
      bash -s -- --skip-config --dir="${LOCAL_BIN_DIR}"
  fi
fi

if ! command -v codebase-memory-mcp >/dev/null 2>&1 && [ ! -x "${LOCAL_BIN_DIR}/codebase-memory-mcp" ]; then
  echo "Warning: codebase-memory-mcp is still not installed."
  echo "Run \`codebase install-runtime\` later."
fi

echo
echo "Installed CLI: ${LOCAL_BIN_DIR}/codebase"
echo "Try:"
echo "  codebase --help"
echo

# --- Optional skill installation ---
echo "A skill file tells AI agents (Claude Code, Codex, OpenCode) how to use the codebase CLI."
read -r -p "Install skill file now? [y/N] " install_skill || true
if [[ "${install_skill:-n}" =~ ^[Yy] ]]; then
  SKILL_NAME="codebase"

  if [[ -f "${INSTALL_DIR}/scripts/install-skill.sh" ]]; then
    echo
    bash "${INSTALL_DIR}/scripts/install-skill.sh"
  else
    echo
    echo "Where should the skill be installed?"
    echo "  1) ~/.agent/skills         (default)"
    echo "  2) ~/.claude/skills        (Claude Code)"
    echo "  3) ~/.codex/skills         (Codex)"
    echo "  4) ~/.opencode/skills      (OpenCode)"
    echo "  5) ~/.cc-switch/skills     (cc-switch)"
    echo "  6) custom path"
    echo
    read -r -p "Choice [1-6] (default: 1): " skill_choice || true

    case "${skill_choice:-1}" in
      1) SKILL_HOME="${HOME}/.agent/skills" ;;
      2) SKILL_HOME="${HOME}/.claude/skills" ;;
      3) SKILL_HOME="${HOME}/.codex/skills" ;;
      4) SKILL_HOME="${HOME}/.opencode/skills" ;;
      5) SKILL_HOME="${HOME}/.cc-switch/skills" ;;
      6)
        read -r -p "Enter path: " custom_path || true
        SKILL_HOME="${custom_path/#\~/$HOME}"
        ;;
      *) SKILL_HOME="${HOME}/.agent/skills" ;;
    esac

    SKILL_DIR="${SKILL_HOME}/${SKILL_NAME}"
    mkdir -p "${SKILL_DIR}"
    curl -fsSL "https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}/skill/SKILL.md" \
      -o "${SKILL_DIR}/SKILL.md"
    echo "Installed: ${SKILL_DIR}/SKILL.md"
  fi
fi
