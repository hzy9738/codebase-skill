# Releasing

## Version files

Update both files together:

- `pyproject.toml`
- `src/codebase_cli/cli.py`

## Pre-release checks

Run from the repository root:

```bash
bash tests/smoke_test.sh
python3 -m build
python3 -m pip install --target "$(mktemp -d)" .
```

If you changed the installer, also verify:

```bash
TMP_HOME="$(mktemp -d)"
HOME="$TMP_HOME" PYTHONUSERBASE="$TMP_HOME/.local" bash scripts/install.sh --install-skill --skip-upstream-install
```

## GitHub release checklist

1. Ensure `README.md`, `CONTRIBUTING.md`, and `RELEASING.md` match current behavior.
2. Update version numbers.
3. Run all checks.
4. Commit with a release commit, for example: `release: v0.4.0`.
5. Tag the release, for example: `git tag v0.4.0`.
6. Push branch and tag.
7. Publish a GitHub release using the tag.

## Suggested first release title

```text
v0.4.0: initial public release
```

## Suggested first release notes

```text
codebase-skill is a CLI-first local wrapper around codebase-memory-mcp with optional Codex skill integration.

Highlights:
- repository-local index storage under .codex/cbm/
- global codebase command with refresh, search, call graph, and snippet workflows
- optional ~/.cc-switch/skills/codebase installation for Codex users
- macOS and Ubuntu 24 friendly install path

This release targets agent-heavy repository retrieval without runtime MCP protocol overhead.
```
