# codebase-skill

Languages: **English** | [简体中文](README.zh-CN.md)

> CLI-first local code indexing for agent workflows, backed by `codebase-memory-mcp`.

`codebase-skill` is a local CLI wrapper for the official [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp) project, with an optional multi-tool skill stub.

It keeps indexes inside the current repository under `.codebase/`, exposes a global `codebase` command, and avoids the MCP protocol at runtime.

Quick links: [Install](#install) · [Quick start](#quick-start) · [Optional skill](#optional-skill-installation) · [Development](#development) · [GitHub publishing](#github-publishing)

## At a glance

| Area | Decision |
| --- | --- |
| Index storage | Project-local `.codebase/<uuid>/` |
| Runtime model | Local CLI, no MCP protocol at runtime |
| Upstream engine | `DeusData/codebase-memory-mcp` |
| Primary interface | `codebase` shell command |
| Agent integration | Optional `~/.agents/skills/codebase/SKILL.md` (multi-tool) |
| Target workflow | Codex, Claude Code, OpenCode, Copilot, local CLI |

## What you get

- Project-local index storage under `.codebase/<uuid>/`
- A normal shell command: `codebase`
- Optional multi-tool skill install under `~/.agents/skills/codebase`
- Better defaults for agent workflows: `func`, `calls`, `snippet`, `search-code`, `detect-changes`, `refresh`
- No git dependency, no runtime MCP server requirement

## Positioning

`codebase-memory-mcp` is still the real indexer and graph engine. This repo adds:

- project-local storage conventions
- a CLI-first workflow that agents can call directly
- refresh metadata
- a small optional skill stub for Claude Code, Codex, OpenCode, and similar tools

If you want raw upstream behavior, call the upstream tool directly. If you want a pragmatic local retrieval workflow for Codex, Claude Code, OpenCode, Copilot, or plain shell use, use this repo.

## Why this repo exists

This project is for teams or individuals who want code-index style retrieval without turning every lookup into an MCP round trip.

- Keep indexing local to the repository instead of scattering state elsewhere.
- Give agents a stable `codebase` command instead of a protocol dependency.
- Keep repo instructions simple: use `codebase` first, then fall back to `rg`.
- Reuse the upstream graph/index engine without inheriting MCP runtime overhead.

## Install

### Prerequisites (macOS)

```bash
brew install python
```

### Prerequisites (Ubuntu 24.04)

```bash
sudo apt update
sudo apt install -y curl python3 python3-pip
```

### One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/hzy9738/codebase-skill/main/scripts/install.sh | bash
```

The installer:

- installs this package with `python3 -m pip install --user`
- retries with `--break-system-packages` on PEP 668 style Python environments when needed
- keeps the executable at `~/.local/bin/codebase`
- installs upstream `codebase-memory-mcp` when possible during setup

### Install from a local clone

```bash
git clone https://github.com/hzy9738/codebase-skill.git
cd codebase-skill
bash scripts/install.sh
```

## Quick start

```bash
codebase index --mode moderate
codebase func login
codebase calls login --direction both
codebase snippet login
codebase search-code redis --file-pattern '*.go'
codebase detect-changes
codebase refresh
```

Useful diagnostics:

```bash
codebase self-check
codebase status
codebase --version
```

## How it works in a project

`codebase` writes indexes under the current working directory:

```text
<project>/.codebase/
  d0f7ca83-c52c-450e-8cc0-4f4f2f3313b8/
    index/*.db
    metadata.json
  019da154-2915-7413-852c-230622b512f4/
    index/*.db
    metadata.json
```

Typical workflow:

1. Run `codebase index` once on a fresh project.
2. Use `codebase func` to discover candidate functions or methods.
3. Use `codebase calls` and `codebase snippet` after symbol resolution.
4. Use `codebase search-code` for text-oriented retrieval.
5. Use `codebase refresh` instead of repeated full re-indexes.

Session behavior:

- Index data is isolated per session under `<project>/.codebase/<uuid>/`.
- Session UUIDs are auto-detected from the parent agent process (Claude Code, Codex, OpenCode) via PID lookup, or generated automatically.
- Use `codebase --session <id> ...` or `CODEBASE_SESSION=<id>` to override.
- There is no automatic runtime download on first use. Install the upstream binary explicitly with `codebase install-runtime` if it is missing.

## Optional skill installation

`codebase` is CLI-first — you can call the `codebase` command directly from any agent that runs shell commands. The skill wrapper is optional and intentionally tiny.

To install the skill file interactively:

```bash
bash scripts/install-skill.sh
```

This prompts you to choose a target directory:

- `~/.agents/skills` (default)
- `~/.claude/skills` (Claude Code)
- `~/.codex/skills` (Codex)
- `~/.opencode/skills` (OpenCode)
- `~/.cc-switch/skills` (cc-switch)
- or a custom path

You can also pass the path directly:

```bash
bash scripts/install-skill.sh ~/.claude/skills
```

Recommended `AGENTS.md` rule:

```md
- 内部代码和文档检索优先使用 `codebase` skill，不可用或无结果时再降级到 `rg`、`fd` 或其他命令。
```

## Commands

- `status`: show project, cache, metadata, and index state
- `install-runtime`: explicitly install `codebase-memory-mcp` into `~/.local/bin`
- `index`: build or rebuild the local index
- `refresh`: rebuild only when the index is missing or mode changed
- `projects`: list indexed projects in the current local cache
- `reset`: delete `.codebase`
- `self-check`: verify PATH, dependencies, session detection, and index wiring
- `func`: search indexed functions and methods
- `calls`: show callers and callees for a resolved symbol
- `snippet`: print the source snippet for a symbol
- `search-code`: text/code search with graph-aware ranking
- `search-graph`: direct wrapper for upstream `search_graph`
- `trace-path`: direct wrapper for upstream `trace_path`
- `query-graph`: direct wrapper for upstream `query_graph`
- `detect-changes`: show changed files and impacted symbols
- `architecture`: print upstream architecture summary
- `schema`: print graph schema summary
- `index-status`: show upstream index status
- `adr`: get or update ADR content through upstream `manage_adr`
- `ingest-traces`: forward runtime traces to upstream `ingest_traces`

Runtime resolution order:

1. `CBM_CODEBASE_MEMORY_BIN`
2. `codebase-memory-mcp` from `PATH`
3. `~/.local/bin/codebase-memory-mcp`

## Development

Run the local checks:

```bash
bash tests/smoke_test.sh
```

Run the wrapper without installing:

```bash
bin/codebase --help
```

Contribution and release workflow:

- see `CONTRIBUTING.md`
- see `RELEASING.md`

## GitHub publishing

Copy-ready GitHub repository metadata, About text, topics, and first-release copy live in `GITHUB_PUBLICATION.md`.

## Limitations

- Index quality and graph behavior still depend on `DeusData/codebase-memory-mcp`
- First-time indexing cost is mostly the upstream indexer cost
- `ingest-traces` depends on current upstream runtime edge support
- This repo is not a replacement for `rg`; it is the indexed retrieval layer you use before falling back

## License

MIT
