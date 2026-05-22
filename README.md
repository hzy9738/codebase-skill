# codebase-skill

Languages: **English** | [简体中文](README.zh-CN.md)

> A lightweight Node.js CLI that brings deep code retrieval to your terminal — no Python, no MCP protocol at runtime.

`codebase-skill` wraps the official [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp) engine into a simple `codebase` command. Indexes live inside your project under `.codebase/`, sessions are auto-detected, and everything works over plain CLI.

Quick links: [Install](#install) · [Quick start](#quick-start) · [Optional skill](#optional-skill-installation) · [Development](#development) · [GitHub publishing](#github-publishing)

## At a glance

| Area | Decision |
| --- | --- |
| Language | Node.js (zero Python dependency) |
| Index storage | Project-local `.codebase/<uuid>/` |
| Runtime model | Local CLI, no MCP protocol at runtime |
| Upstream engine | `DeusData/codebase-memory-mcp` |
| Primary interface | `codebase` shell command |
| Agent integration | Optional `~/.agents/skills/codebase/SKILL.md` |
| Target workflow | Codex, Claude Code, OpenCode, Copilot, shell |

## What you get

- A single `codebase` command that works anywhere
- Project-local indexes under `.codebase/<uuid>/`
- Agent-friendly defaults: `func`, `calls`, `snippet`, `search-code`, `detect-changes`, `refresh`
- Optional skill stub for multi-tool agents
- No git dependency, no runtime MCP server, no Python

## Positioning

`codebase-memory-mcp` is the real indexer and graph engine. This repo adds:

- project-local storage conventions
- a CLI-first workflow agents can call directly
- refresh metadata
- a small skill stub for Claude Code, Codex, OpenCode, and similar tools

Use the upstream tool directly if you want raw behavior. Use this repo if you want a pragmatic local retrieval workflow.

## Why this repo exists

For teams and individuals who want code-index retrieval without turning every lookup into an MCP round trip:

- Keep indexes local to the repository instead of scattering state elsewhere
- Give agents a stable `codebase` command instead of a protocol dependency
- Keep instructions simple: `codebase` first, then fall back to `rg`
- Reuse the upstream engine without inheriting MCP runtime overhead

## Install

### Prerequisites

Node.js >= 19 is required. Install it with your preferred method:

```bash
# macOS
brew install node

# Linux (Ubuntu)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Or use nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
nvm install 22
```

### One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/hzy9738/codebase-skill/main/scripts/install.sh | bash
```

The installer will:

- Check that Node.js >= 19 is available
- Copy the `codebase` CLI to `~/.local/bin/codebase`
- Install upstream `codebase-memory-mcp` if not already present
- Optionally prompt to install the agent skill file

### Install from a local clone

```bash
git clone https://github.com/hzy9738/codebase-skill.git
cd codebase-skill
bash scripts/install.sh
```

## Quick start

```bash
codebase index --mode moderate   # First time: build the index
codebase func login              # Find functions named "login"
codebase calls login --direction both  # See callers and callees
codebase snippet login           # Show the source
codebase search-code redis --file-pattern '*.go'  # Text search
codebase detect-changes          # What changed since last index?
codebase refresh                 # Update stale indexes
```

Useful diagnostics:

```bash
codebase self-check              # Verify environment is wired correctly
codebase status                  # Show current session index status
codebase --version               # Should print v0.6.1
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

1. Run `codebase index` once on a fresh project
2. Use `codebase func` to discover candidate functions or methods
3. Use `codebase calls` and `codebase snippet` after resolving a symbol
4. Use `codebase search-code` for text-oriented retrieval
5. Use `codebase refresh` instead of repeated full re-indexes

Session behavior:

- Index data is isolated per session under `<project>/.codebase/<uuid>/`
- Session UUIDs are auto-detected from the parent agent process (Claude Code, Codex, OpenCode) via PID lookup
- Use `codebase --session <id> ...` or `CODEBASE_SESSION=<id>` to override
- There is no automatic runtime download on first use — install upstream once with `codebase install-runtime`

## Optional skill installation

A skill file tells AI agents (Claude Code, Codex, OpenCode) how to use the `codebase` CLI. The installer will prompt you during setup, or you can install it manually:

```bash
bash scripts/install-skill.sh
```

### Supported locations

| Tool | Default path |
| --- | --- |
| General | `~/.agents/skills/codebase/` |
| Claude Code | `~/.claude/skills/codebase/` |
| Codex | `~/.codex/skills/codebase/` |
| OpenCode | `~/.opencode/skills/codebase/` |

After installation, the agent gets a skill stub with:

- Example CLI usage (`func`, `calls`, `snippet`, `refresh`, etc.)
- Instructions to prefer `codebase` then fall back to `rg`
- Session and index workflow guidance

## Advanced usage

```bash
# Check upstream health
codebase index-status

# Architecture overview
codebase architecture

# Run a raw graph query
codebase query-graph

# Ingest runtime traces
codebase ingest-traces traces.json
```

## Development

```bash
git clone https://github.com/hzy9738/codebase-skill.git
cd codebase-skill

# Run locally
node bin/codebase --version
node bin/codebase --help

# Install from local clone
bash scripts/install.sh

# Run smoke test
bash tests/smoke_test.sh
```

### Project structure

```text
bin/codebase          # The CLI entry point (standalone Node.js)
src/cli.js            # Modular CLI implementation
scripts/install.sh    # One-line installer
scripts/install-skill.sh  # Skill stub installer
skill/SKILL.md        # Agent skill definition
tests/                # Smoke tests
```

## GitHub publishing

> See [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md) for detailed publishing instructions.

Quick checklist:

- [ ] Update `version` in `package.json`
- [ ] Tag the release: `git tag v0.6.1 && git push origin v0.6.1`
- [ ] Verify the installer: `curl -fsSL .../install.sh | bash`

## Releasing

See [RELEASING.md](RELEASING.md) for the full release workflow.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)