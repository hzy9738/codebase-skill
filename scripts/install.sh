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
    if ! command -v brew >/dev/null 2>&1; then
      echo "Homebrew not found. Install it first: https://brew.sh" >&2
      exit 1
    fi

    local versions
    versions="$(brew search '/python@3\.' 2>/dev/null | grep -E '^python@3\.[0-9]+$' | sort -V -r || true)"
    if [[ -z "${versions}" ]]; then
      versions="python@3.13 python@3.12 python@3.11"
    fi

    local pkg
    if [[ -t 0 ]]; then
      echo "Available Python versions via Homebrew:"
      echo
      echo "${versions}" | awk '{printf "  %d) %s\n", NR, $0}'
      local count
      count="$(echo "${versions}" | wc -l | tr -d ' ')"
      echo "  $((count + 1))) custom"
      echo
      read -r -p "Choose version [1-$((count + 1))] (default: 1): " ver_choice || true

      if [[ -z "${ver_choice}" ]] || [[ "${ver_choice}" == "1" ]]; then
        pkg="$(echo "${versions}" | head -1)"
      elif [[ "${ver_choice}" -le "${count}" ]] 2>/dev/null; then
        pkg="$(echo "${versions}" | sed -n "${ver_choice}p")"
      else
        read -r -p "Enter package name: " pkg || true
        if [[ -z "${pkg}" ]]; then
          echo "No package specified." >&2
          exit 1
        fi
      fi
    else
      echo "Non-interactive mode: auto-selecting latest Python version"
      pkg="$(echo "${versions}" | head -1)"
    fi

    echo
    echo "==> brew install ${pkg}"
    brew install "${pkg}" || {
      echo "brew install ${pkg} failed." >&2
      exit 1
    }

  elif [[ "${os_name}" == "Linux" ]]; then
    if ! command -v apt-get >/dev/null 2>&1; then
      echo "Unsupported Linux package manager. Please install python3 manually." >&2
      exit 1
    fi

    local pkg
    if [[ -t 0 ]]; then
      echo "Available Python versions via apt:"
      echo
      echo "  1) python3        (system default, recommended)"
      echo "  2) python3.12"
      echo "  3) python3.11"
      echo "  4) custom"
      echo
      read -r -p "Choose version [1-4] (default: 1): " ver_choice || true

      case "${ver_choice:-1}" in
        1) pkg="python3 python3-pip" ;;
        2) pkg="python3.12 python3-pip" ;;
        3) pkg="python3.11 python3-pip" ;;
        4)
          read -r -p "Enter package name(s): " pkg || true
          if [[ -z "${pkg}" ]]; then
            echo "No package specified." >&2
            exit 1
          fi
          ;;
        *) pkg="python3 python3-pip" ;;
      esac
    else
      echo "Non-interactive mode: auto-selecting python3 (system default)"
      pkg="python3 python3-pip"
    fi

    echo
    echo "==> sudo apt-get update && sudo apt-get install -y ${pkg}"
    sudo apt-get update && sudo apt-get install -y ${pkg} || {
      echo "apt-get install failed." >&2
      exit 1
    }
  fi

  # After install, find the best python3 binary
  for candidate in "${want_bin}" python3 python3.13 python3.12 python3.11; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      PYTHON_BIN="${candidate}"
      echo "Using: ${PYTHON_BIN} ($(${PYTHON_BIN} --version 2>&1))"
      return 0
    fi
  done
  echo "Python installation seems to have failed. Check and re-run." >&2
  exit 1
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
if [[ -t 0 ]]; then
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
      echo "  1) ~/.agents/skills         (default)"
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
else
  echo "Non-interactive mode: skipping skill installation."
  echo "Run \`bash scripts/install-skill.sh\` manually to install the skill file for AI agents."
fi
