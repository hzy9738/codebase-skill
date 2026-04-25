# codebase-skill

Languages: **English** | [简体中文](README.zh-CN.md)

> CLI-first local code indexing for Codex and agent workflows, backed by `codebase-memory-mcp`.

`codebase-skill` is a local CLI plus an optional Codex skill wrapper for the official [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp) project.

It keeps indexes inside the current repository under `.codex/cbm/`, exposes a global `codebase` command, and avoids the MCP protocol at runtime.

Quick links: [Install](#install) · [Quick start](#quick-start) · [Codex skill integration](#codex-skill-integration) · [Development](#development) · [GitHub publishing](#github-publishing)

## At a glance

| Area | Decision |
| --- | --- |
| Index storage | Repository-local `.codex/cbm/` |
| Runtime model | Local CLI, no MCP protocol at runtime |
| Upstream engine | `DeusData/codebase-memory-mcp` |
| Primary interface | `codebase` shell command |
| Agent integration | Optional `~/.cc-switch/skills/codebase/SKILL.md` |
| Target workflow | Codex, local CLI, agent-heavy repository retrieval |

## What you get

- Repository-local index storage under `.codex/cbm/`
- A normal shell command: `codebase`
- Optional Codex skill install under `~/.cc-switch/skills/codebase`
- Better defaults for agent workflows: `func`, `calls`, `snippet`, `search-code`, `detect-changes`, `refresh`
- No GitHub artifact flow and no runtime MCP server requirement

## Positioning

`codebase-memory-mcp` is still the real indexer and graph engine. This repo adds:

- project-local storage conventions
- a CLI-first workflow that agents can call directly
- refresh metadata and dirty-worktree detection
- a small skill stub that tells Codex to use the `codebase` command first

If you want raw upstream behavior, call the upstream tool directly. If you want a pragmatic local retrieval workflow for Codex, use this repo.

## Why this repo exists

This project is for teams or individuals who want code-index style retrieval without turning every lookup into an MCP round trip.

- Keep indexing local to the repository instead of scattering state elsewhere.
- Give agents a stable `codebase` command instead of a protocol dependency.
- Keep `AGENTS.md` simple: use `codebase` first, then fall back to `rg`.
- Reuse the upstream graph/index engine without inheriting MCP runtime overhead.

## Install

### macOS

```bash
brew install git python
```

### Ubuntu 24.04

```bash
sudo apt update
sudo apt install -y curl git python3 python3-pip
```

### Install the CLI

From a local clone:

```bash
git clone <your-repo-url> codebase-skill
cd codebase-skill
python3 -m pip install --user .
```

Or use the bundled installer:

```bash
bash scripts/install.sh
```

The installer:

- installs this package with `python3 -m pip install --user`
- retries with `--break-system-packages` on PEP 668 style Python environments when needed
- keeps the executable at `~/.local/bin/codebase`
- installs upstream `codebase-memory-mcp` only when neither `codebase-memory-mcp` nor `uvx` is available

If you want the Codex skill as well:

```bash
bash scripts/install.sh --install-skill
```

## Quick start

Inside a git repository:

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

`codebase` auto-detects the current git repository and writes only to:

```text
<repo>/.codex/cbm/
  index/*.db
  metadata.json
```

If you do not want `.codex/` to appear in `git status`, add a local-only exclude:

```bash
printf '\n.codex/\n' >> .git/info/exclude
```

Typical workflow:

1. Run `codebase index` once on a fresh repository.
2. Use `codebase func` to discover candidate functions or methods.
3. Use `codebase calls` and `codebase snippet` after symbol resolution.
4. Use `codebase search-code` for text-oriented retrieval.
5. Use `codebase refresh` instead of repeated full re-indexes.

## Codex skill integration

This repo is CLI-first. The skill is optional and intentionally tiny.

Install the skill:

```bash
bash scripts/install.sh --install-skill
```

That writes:

```text
~/.cc-switch/skills/codebase/SKILL.md
```

Recommended `AGENTS.md` rule:

```md
- 内部代码和文档检索优先使用 `codebase` skill，不可用或无结果时再降级到 `rg`、`fd` 或其他命令。
```

This keeps your agent guidance short while still making `codebase` the default indexed retrieval path.

## Commands

- `status`: show repository, cache, metadata, and index state
- `index`: build or rebuild the local index
- `refresh`: rebuild only when the repo or index mode changed
- `projects`: list indexed projects in the current local cache
- `reset`: delete `.codex/cbm`
- `self-check`: verify PATH, dependencies, repo detection, and index wiring
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
