# GitHub Publication

## Repository name

Recommended:

```text
codebase-skill
```

If you want the name to emphasize the CLI more than the skill:

```text
codebase-cli-skill
```

## About

### Short description

```text
CLI-first local wrapper for codebase-memory-mcp with optional Codex skill integration.
```

### Longer About text

```text
Repository-local code indexing and graph retrieval for Codex and agent workflows. Uses codebase-memory-mcp as the engine, stores indexes under .codex/cbm/, and avoids MCP protocol overhead at runtime.
```

## Topics

Recommended GitHub topics:

```text
codex
agent-tools
developer-tools
python-cli
code-search
code-indexing
codebase-memory-mcp
```

## Social preview text

```text
Local code indexing for Codex: repository-scoped, CLI-first, MCP-free at runtime.
```

## Pinned feature bullets

Useful for the top of the README, repository sidebar copy, or launch post:

- repository-local index storage under `.codex/cbm/`
- `codebase` shell command for search, call graph traversal, snippets, and refresh
- optional `codebase` skill install for Codex
- built on `DeusData/codebase-memory-mcp`, without requiring MCP at runtime
- macOS and Ubuntu 24 friendly install path

## First release

### Title

```text
v0.4.0: initial public release
```

### Body

```text
codebase-skill is a CLI-first local wrapper around codebase-memory-mcp with optional Codex skill integration.

Highlights:
- repository-local index storage under .codex/cbm/
- global codebase command with refresh, function lookup, call graph traversal, snippets, and code search
- optional ~/.cc-switch/skills/codebase installation for Codex users
- macOS and Ubuntu 24 friendly installation
- no MCP protocol required at runtime

Why this exists:
- reduce runtime overhead compared with MCP-first retrieval flows
- keep AGENTS.md simple for Codex-driven repositories
- preserve project-local indexing behavior instead of pushing state into external services

Validation:
- smoke tests pass
- package builds as sdist and wheel
- installer verified in a clean temporary HOME
```

## Suggested launch blurb

```text
Open-sourced a small but pragmatic tool: codebase-skill. It wraps codebase-memory-mcp behind a local codebase CLI and an optional Codex skill, keeps indexes in .codex/cbm/, and avoids MCP protocol overhead during normal repository retrieval.
```
