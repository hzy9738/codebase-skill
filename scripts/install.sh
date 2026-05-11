#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-hzy9738}"
REPO_NAME="${REPO_NAME:-codebase-skill}"
REPO_BRANCH="${REPO_BRANCH:-main}"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}"

LOCAL_BIN_DIR="${LOCAL_BIN_DIR:-${HOME}/.local/bin}"
INSTALL_UPSTREAM="${INSTALL_UPSTREAM:-1}"

usage() {
  cat <<'EOF'
Usage:
  curl -fsSL <install-url> | bash
  curl -fsSL <install-url> | bash -s -- [options]

Options:
  --skip-upstream-install   Do not install codebase-memory-mcp during setup
  --help                    Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-upstream-install)
      INSTALL_UPSTREAM=0
      shift
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

# --- Ensure Node.js is available ---
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
  echo
  echo "Install Node.js with one of the following:"
  echo "  macOS:  brew install node"
  echo "  Linux:  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs"
  echo
  echo "Or use nvm: https://github.com/nvm-sh/nvm"
  exit 1
}
ensure_node

# --- Prepare install source ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."

if [[ -f "${ROOT_DIR}/package.json" ]] && [[ -f "${ROOT_DIR}/src/cli.mjs" ]]; then
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

# --- Install package globally ---
install_global() {
  echo "==> Installing globally via npm link..."
  cd "${INSTALL_DIR}"
  
  # Create a temporary directory for global install
  local tmp_global
  tmp_global="$(mktemp -d)"
  
  # Copy the package into temporary directory
  cp -r "${INSTALL_DIR}/package.json" "${INSTALL_DIR}/bin" "${INSTALL_DIR}/src" "${tmp_global}/"
  
  # Install globally
  cd "${tmp_global}"
  if npm install -g .; then
    echo "✓ Global installation successful"
  else
    echo "Global installation via npm failed. Trying local symlink approach..."
    
    # Fallback: symlink bin/codebase to ~/.local/bin
    mkdir -p "${LOCAL_BIN_DIR}"
    ln -sf "${INSTALL_DIR}/bin/codebase" "${LOCAL_BIN_DIR}/codebase" || {
      echo "Failed to create symlink."
      exit 1
    }
    echo "✓ Symlink created at ${LOCAL_BIN_DIR}/codebase"
  fi
  
  rm -rf "${tmp_global}"
}

mkdir -p "${LOCAL_BIN_DIR}"
install_global

if [[ ":${PATH}:" != *":${LOCAL_BIN_DIR}:"* ]]; then
  echo
  echo "Add ${LOCAL_BIN_DIR} to PATH if needed:"
  echo "  echo 'export PATH=\"${LOCAL_BIN_DIR}:\$PATH\"' >> ~/.bashrc"
fi

# --- Install upstream codebase-memory-mcp ---
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
      bash "${INSTALL_DIR}/scripts/install-skill.sh"
    else
      echo "Skill installer not found in ${INSTALL_DIR}/scripts/install-skill.sh"
    fi
  fi
fi