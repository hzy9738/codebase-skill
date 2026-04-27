#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-hzy9738}"
REPO_NAME="${REPO_NAME:-codebase-skill}"
REPO_BRANCH="${REPO_BRANCH:-main}"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}"

LOCAL_BIN_DIR="${HOME}/.local/bin"
SKILL_HOME_DEFAULT="${HOME}/.codex/skills"
SKILL_NAME="codebase"
INSTALL_SKILL=0
INSTALL_UPSTREAM=1
PYTHON_BIN="${PYTHON_BIN:-python3}"
SKILL_HOME="${SKILL_HOME_DEFAULT}"

usage() {
  cat <<'EOF'
Usage:
  curl -fsSL <install-url> | bash
  curl -fsSL <install-url> | bash -s -- [options]

Options:
  --install-skill           Install the Codex skill stub under ~/.codex/skills/codebase
  --skill-home <path>       Override the skill home directory
  --skip-upstream-install   Do not install codebase-memory-mcp during setup
  --python <path>           Python executable to use
  --help                    Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-skill)
      INSTALL_SKILL=1
      shift
      ;;
    --skill-home)
      SKILL_HOME="$2"
      shift 2
      ;;
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

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Missing Python executable: ${PYTHON_BIN}" >&2
  exit 1
fi

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
  SKILL_SRC="${ROOT_DIR}/skill/SKILL.md"
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
  SKILL_SRC="${INSTALL_DIR}/skill/SKILL.md"
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

if [[ "${INSTALL_UPSTREAM}" == "1" ]] && \
   ! command -v codebase-memory-mcp >/dev/null 2>&1; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "Skipping codebase-memory-mcp install because curl is unavailable." >&2
    echo "Run \`codebase install-runtime\` later after curl/proxy is ready." >&2
  else
    curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | \
      bash -s -- --skip-config --dir="${LOCAL_BIN_DIR}"
  fi
fi

if ! command -v codebase-memory-mcp >/dev/null 2>&1 && [ ! -x "${LOCAL_BIN_DIR}/codebase-memory-mcp" ]; then
  echo "Warning: codebase-memory-mcp is still not installed."
  echo "Run \`codebase install-runtime\` or rerun this script after network/proxy is ready."
fi

if [[ "${INSTALL_SKILL}" == "1" ]]; then
  SKILL_DIR="${SKILL_HOME%/}/${SKILL_NAME}"
  mkdir -p "${SKILL_DIR}"
  if [[ -f "${SKILL_SRC}" ]]; then
    cp "${SKILL_SRC}" "${SKILL_DIR}/SKILL.md"
  else
    echo "==> Downloading skill definition..."
    curl -fsSL "https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}/skill/SKILL.md" \
      -o "${SKILL_DIR}/SKILL.md"
  fi
  echo "Installed skill: ${SKILL_DIR}/SKILL.md"
fi

SHELL_NAME="$(basename "${SHELL:-bash}")"
RC_FILE="${HOME}/.bashrc"
if [[ "${SHELL_NAME}" == "zsh" ]]; then
  RC_FILE="${HOME}/.zshrc"
fi

if [[ ":${PATH}:" != *":${LOCAL_BIN_DIR}:"* ]]; then
  echo
  echo "Add ${LOCAL_BIN_DIR} to PATH if needed:"
  echo "  echo 'export PATH=\"${LOCAL_BIN_DIR}:\$PATH\"' >> ${RC_FILE}"
fi

echo
echo "Installed CLI: ${LOCAL_BIN_DIR}/codebase"
echo "Try:"
echo "  codebase --help"
