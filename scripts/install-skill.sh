#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="codebase"
DEFAULT_SKILL_HOME="${HOME}/.agent/skills"

REPO_OWNER="${REPO_OWNER:-hzy9738}"
REPO_NAME="${REPO_NAME:-codebase-skill}"
REPO_BRANCH="${REPO_BRANCH:-main}"
SKILL_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}/skill/SKILL.md"

echo "==> codebase skill installer"
echo

if [[ $# -gt 0 ]]; then
  SKILL_HOME="$1"
  echo "Installing to: ${SKILL_HOME}/${SKILL_NAME}/"
else
  echo "Where should the skill be installed?"
  echo
  echo "  1) ~/.agent/skills         (default)"
  echo "  2) ~/.claude/skills        (Claude Code)"
  echo "  3) ~/.codex/skills         (Codex)"
  echo "  4) ~/.opencode/skills      (OpenCode)"
  echo "  5) ~/.cc-switch/skills     (cc-switch)"
  echo "  6) custom path"
  echo
  read -r -p "Choice [1-6] (default: 1): " choice

  case "${choice:-1}" in
    1) SKILL_HOME="${HOME}/.agent/skills" ;;
    2) SKILL_HOME="${HOME}/.claude/skills" ;;
    3) SKILL_HOME="${HOME}/.codex/skills" ;;
    4) SKILL_HOME="${HOME}/.opencode/skills" ;;
    5) SKILL_HOME="${HOME}/.cc-switch/skills" ;;
    6)
      read -r -p "Enter path: " custom_path
      SKILL_HOME="${custom_path/#\~/$HOME}"
      ;;
    *)
      echo "Invalid choice, using default." >&2
      SKILL_HOME="${DEFAULT_SKILL_HOME}"
      ;;
  esac

  echo
  echo "Target: ${SKILL_HOME}/${SKILL_NAME}/SKILL.md"
  read -r -p "Confirm install? [Y/n] " confirm
  if [[ "${confirm:-y}" =~ ^[Nn] ]]; then
    echo "Cancelled."
    exit 0
  fi
fi

SKILL_DIR="${SKILL_HOME}/${SKILL_NAME}"
mkdir -p "${SKILL_DIR}"

if [[ -f "${BASH_SOURCE[0]:-.}/../../skill/SKILL.md" ]]; then
  SKILL_SRC="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)/../skill/SKILL.md"
  cp "${SKILL_SRC}" "${SKILL_DIR}/SKILL.md"
else
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required for remote skill installation." >&2
    exit 1
  fi
  curl -fsSL "${SKILL_URL}" -o "${SKILL_DIR}/SKILL.md"
fi

echo
echo "Installed: ${SKILL_DIR}/SKILL.md"
