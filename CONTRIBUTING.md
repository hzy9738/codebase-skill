# Contributing

## Scope

This project is intentionally narrow:

- keep `codebase` CLI-first
- keep Codex skill integration optional
- keep index data repository-local under `.codex/cbm/`
- avoid adding runtime MCP protocol requirements

Changes that increase complexity should justify the maintenance cost clearly.

## Development setup

```bash
git clone <your-repo-url> codebase-skill
cd codebase-skill
python3 -m pip install --user -e .
```

If you want the local wrapper without installing:

```bash
bin/codebase --help
```

## Before opening a PR

Run:

```bash
bash tests/smoke_test.sh
```

If you change packaging, install, or entrypoint behavior, also verify:

```bash
python3 -m build
python3 -m pip install --target "$(mktemp -d)" .
```

If you change repo detection, indexing, or refresh behavior, test against a real git repository instead of relying only on unit tests.

## Change guidelines

- Preserve the `codebase` command surface unless there is a strong compatibility reason.
- Prefer small wrappers over large custom indexing logic.
- Keep the skill stub minimal. Workflow detail should live in the CLI and README, not in a long skill prompt.
- Do not add project-level index files outside `.codex/cbm/`.
- Keep macOS and Ubuntu 24 support working together.

## Pull requests

PRs are easier to review when they include:

- the problem statement
- the user-facing behavior change
- any compatibility risk
- exact verification commands you ran

## Release expectations

Version changes should update both:

- `pyproject.toml`
- `src/codebase_cli/cli.py`

Release steps are documented in `RELEASING.md`.
