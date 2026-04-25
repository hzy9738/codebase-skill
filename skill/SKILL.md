---
name: codebase
description: Repository-local deep code retrieval skill that uses the global `codebase` CLI instead of MCP. Use when you need indexed function lookup, call graph traversal, code snippets, code search, architecture summaries, or change impact analysis inside a git repo. Prefer this before `rg` when the local `.codebase/` index exists or can be created.
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

- Run inside a git repository.
- On a fresh repo, start with `codebase index --mode moderate` or `codebase index --mode full`.
- Prefer `codebase refresh` once a repo is already indexed.
- Use `func` to find symbols, `calls` to traverse graph edges, and `snippet` to inspect source.
- Use `search-code` for indexed text retrieval.
- Fall back to `rg` only when `codebase` is unavailable or returns no useful result.

## Notes

- All local index data lives under `<repo>/.codebase/`.
- Older `.codex/cbm/` layouts are migrated to `.codebase/` automatically on first use.
- Add `.codebase/` to `.git/info/exclude` if you do not want it in `git status`.
- `search-graph`, `trace-path`, `query-graph`, `architecture`, `schema`, `index-status`, `adr`, and `ingest-traces` expose more of the upstream tool surface when needed.
