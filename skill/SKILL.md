---
name: codebase
description: Repository-local deep code retrieval skill that uses the global `codebase` CLI instead of MCP. Use when you need indexed function lookup, call graph traversal, code snippets, code search, architecture summaries, or change impact analysis. Prefer this before `rg` when the local `.codebase/` index exists or can be created.
---

# Codebase

Use this skill when you want deeper repository retrieval than plain text grep, but do not want runtime MCP.

## Quick start

```bash
codebase status
codebase refresh
codebase func auth
codebase calls createUser --direction both
codebase snippet createUser
codebase search-code redis --file-pattern '*.go'
codebase detect-changes
```

## Workflow

- Index data lives under `<project>/.codebase/<uuid>/`.
- Session names are UUIDs auto-detected from the parent agent process (Claude Code, Codex, OpenCode), or generated automatically. Use `codebase --session <id> ...` or `CODEBASE_SESSION=<id>` to override.
- On a fresh project, start with `codebase index --mode moderate` or `codebase index --mode full`.
- Prefer `codebase refresh` once a project is already indexed.
- Install `codebase-memory-mcp` with `codebase install-runtime` if it is missing.
- Use `func` to find symbols, `calls` to traverse graph edges, and `snippet` to inspect source.
- Use `search-code` for indexed text retrieval.
- Fall back to `rg` only when `codebase` is unavailable or returns no useful result.

## Notes

- Runtime resolution order is: `CBM_CODEBASE_MEMORY_BIN` -> `PATH` -> `~/.local/bin`.
- Add `.codebase/` to `.git/info/exclude` if you do not want it in `git status`.
- `search-graph`, `trace-path`, `query-graph`, `architecture`, `schema`, `index-status`, `adr`, and `ingest-traces` expose more of the upstream tool surface when needed.
