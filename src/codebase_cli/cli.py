#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_NAME = "codebase"
VERSION = "0.4.1"
INDEX_SUBDIR = Path(".codebase")
LEGACY_INDEX_SUBDIR = Path(".codex") / "cbm"
INDEX_CACHE_DIRNAME = "index"
METADATA_FILENAME = "metadata.json"
FUNCTION_LABELS = {"Function", "Method"}


class ToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepoContext:
    repo_root: Path
    tool_dir: Path
    cache_dir: Path
    metadata_path: Path
    legacy_tool_dir: Path
    legacy_cache_dir: Path
    legacy_metadata_path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def git_output(args: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise ToolError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout.strip()


def git_head_commit(cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def parse_status_path(line: str) -> str:
    path = line[3:].strip() if len(line) >= 4 else line.strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path


def is_tool_work_path(path: str) -> bool:
    normalized = path.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return (
        normalized == INDEX_SUBDIR.as_posix()
        or normalized.startswith(f"{INDEX_SUBDIR.as_posix()}/")
        or normalized == LEGACY_INDEX_SUBDIR.as_posix()
        or normalized.startswith(f"{LEGACY_INDEX_SUBDIR.as_posix()}/")
    )


def repo_has_non_tool_changes(cwd: Path | None = None) -> bool:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False
    for raw_line in proc.stdout.splitlines():
        if not raw_line.strip():
            continue
        if is_tool_work_path(parse_status_path(raw_line)):
            continue
        return True
    return False


def detect_repo_context(cwd: Path | None = None) -> RepoContext:
    repo_root = Path(git_output(["rev-parse", "--show-toplevel"], cwd=cwd)).resolve()
    tool_dir = repo_root / INDEX_SUBDIR
    cache_dir = tool_dir / INDEX_CACHE_DIRNAME
    legacy_tool_dir = repo_root / LEGACY_INDEX_SUBDIR
    return RepoContext(
        repo_root=repo_root,
        tool_dir=tool_dir,
        cache_dir=cache_dir,
        metadata_path=tool_dir / METADATA_FILENAME,
        legacy_tool_dir=legacy_tool_dir,
        legacy_cache_dir=legacy_tool_dir / INDEX_CACHE_DIRNAME,
        legacy_metadata_path=legacy_tool_dir / METADATA_FILENAME,
    )


def migrate_legacy_layout(ctx: RepoContext) -> bool:
    if ctx.tool_dir.exists() or not ctx.legacy_tool_dir.exists():
        return False
    shutil.move(str(ctx.legacy_tool_dir), str(ctx.tool_dir))
    legacy_parent = ctx.legacy_tool_dir.parent
    try:
        legacy_parent.rmdir()
    except OSError:
        pass
    return True


def active_repo_context(cwd: Path | None = None) -> RepoContext:
    ctx = detect_repo_context(cwd)
    migrate_legacy_layout(ctx)
    return ctx


def resolve_cbm_runner() -> list[str]:
    override = os.environ.get("CBM_CODEBASE_MEMORY_BIN")
    if override:
        return shlex.split(override)

    binary = shutil.which("codebase-memory-mcp")
    if binary:
        return [binary]

    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "codebase-memory-mcp"]

    raise ToolError(
        "codebase-memory-mcp not found. Install the binary or make `uvx` available."
    )


def run_command(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise ToolError(f"command failed: {' '.join(cmd)}: {stderr}")
    return proc


def parse_outer_json(output: str) -> dict[str, Any]:
    for raw_line in reversed([line.strip() for line in output.splitlines() if line.strip()]):
        if raw_line.startswith("{") and raw_line.endswith("}"):
            try:
                return json.loads(raw_line)
            except json.JSONDecodeError:
                continue
    raise ToolError(f"unable to parse codebase-memory-mcp output:\n{output}")


def parse_tool_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in payload.get("content", []):
        if item.get("type") == "text" and item.get("text"):
            parts.append(item["text"])
    return "\n".join(parts).strip()


def run_cbm_tool(ctx: RepoContext, tool: str, payload: dict[str, Any] | None = None) -> Any:
    ctx.cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CBM_CACHE_DIR"] = str(ctx.cache_dir)
    runner = resolve_cbm_runner()
    proc = run_command(
        [*runner, "cli", tool, json.dumps(payload or {}, ensure_ascii=False), "--raw"],
        cwd=ctx.repo_root,
        env=env,
        check=False,
    )
    combined = "\n".join(part for part in [proc.stdout, proc.stderr] if part).strip()
    outer = parse_outer_json(combined)
    inner_text = parse_tool_text(outer)

    if inner_text:
        try:
            parsed_inner: Any = json.loads(inner_text)
        except json.JSONDecodeError:
            parsed_inner = {"message": inner_text}
    else:
        parsed_inner = {}

    if proc.returncode != 0 or outer.get("isError"):
        if isinstance(parsed_inner, dict):
            error = parsed_inner.get("error") or parsed_inner.get("message") or inner_text
            hint = parsed_inner.get("hint")
        else:
            error = inner_text or combined
            hint = None
        if hint:
            raise ToolError(f"{error} ({hint})")
        raise ToolError(error or f"{tool} failed")

    return parsed_inner


def list_projects(ctx: RepoContext) -> list[dict[str, Any]]:
    payload = run_cbm_tool(ctx, "list_projects", {})
    return payload.get("projects", [])


def indexed_db_files(ctx: RepoContext) -> list[Path]:
    return sorted(ctx.cache_dir.glob("*.db"))


def resolve_project_name(ctx: RepoContext) -> str:
    projects = list_projects(ctx)
    if not projects:
        raise ToolError(
            f"no index found under {ctx.cache_dir}. Run `codebase index` first."
        )
    if len(projects) > 1:
        names = ", ".join(project["name"] for project in projects)
        raise ToolError(
            f"expected one indexed project in {ctx.cache_dir}, found {len(projects)}: {names}"
        )
    return str(projects[0]["name"])


def ensure_index_exists(ctx: RepoContext) -> None:
    if indexed_db_files(ctx):
        return
    raise ToolError(
        f"no index found under {ctx.cache_dir}. Run `codebase index` first."
    )


def ensure_project_name(ctx: RepoContext) -> str:
    ensure_index_exists(ctx)
    return resolve_project_name(ctx)


def load_metadata(ctx: RepoContext) -> dict[str, Any] | None:
    if not ctx.metadata_path.exists():
        return None
    try:
        return json.loads(ctx.metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid metadata file: {ctx.metadata_path} ({exc})") from exc


def determine_refresh_reason(
    *,
    has_db: bool,
    metadata: dict[str, Any] | None,
    current_head: str,
    repo_dirty: bool,
    requested_mode: str | None = None,
) -> str | None:
    if not has_db:
        return "missing_index"
    if metadata is None:
        return "missing_metadata"
    if requested_mode and metadata.get("mode") != requested_mode:
        return "mode_changed"
    if repo_dirty:
        return "dirty_worktree"
    indexed_head = str(metadata.get("head_commit") or "").strip()
    if current_head and not indexed_head:
        return "missing_head_commit"
    if current_head and indexed_head and indexed_head != current_head:
        return "head_changed"
    return None


def resolve_index_mode(ctx: RepoContext, override_mode: str | None = None) -> str:
    if override_mode:
        return override_mode
    metadata = load_metadata(ctx)
    candidate = metadata.get("mode") if metadata else None
    if candidate in {"full", "moderate", "fast"}:
        return str(candidate)
    return "full"


def write_metadata(ctx: RepoContext, *, mode: str, project_name: str) -> None:
    ctx.tool_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "indexed_at": utc_now(),
        "mode": mode,
        "tool_version": VERSION,
        "repo_root": str(ctx.repo_root),
        "cache_dir": str(ctx.cache_dir),
        "project_name": project_name,
        "head_commit": git_head_commit(ctx.repo_root),
        "db_files": [path.name for path in indexed_db_files(ctx)],
    }
    ctx.metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def perform_index(ctx: RepoContext, *, mode: str, clean: bool = False) -> dict[str, Any]:
    if clean:
        for path in [ctx.tool_dir, ctx.legacy_tool_dir]:
            if path.exists():
                shutil.rmtree(path)
    ctx.cache_dir.mkdir(parents=True, exist_ok=True)

    run_cbm_tool(
        ctx,
        "index_repository",
        {"repo_path": str(ctx.repo_root), "mode": mode},
    )
    project_name = resolve_project_name(ctx)
    write_metadata(ctx, mode=mode, project_name=project_name)
    return {
        "repo_root": str(ctx.repo_root),
        "tool_dir": str(ctx.tool_dir),
        "cache_dir": str(ctx.cache_dir),
        "project_name": project_name,
        "db_files": [path.name for path in indexed_db_files(ctx)],
        "mode": mode,
        "head_commit": git_head_commit(ctx.repo_root),
    }


def search_functions(
    ctx: RepoContext, project_name: str, keyword: str, *, use_regex: bool = False
) -> dict[str, Any]:
    payload: dict[str, Any] = {"project": project_name}
    if use_regex:
        payload["name_pattern"] = keyword
    else:
        payload["query"] = keyword
    response = run_cbm_tool(ctx, "search_graph", payload)
    response["results"] = [
        item for item in response.get("results", []) if item.get("label") in FUNCTION_LABELS
    ]
    response["total"] = len(response["results"])
    response["has_more"] = False
    return response


def resolve_symbol(
    ctx: RepoContext,
    project_name: str,
    symbol: str,
    *,
    treat_as_qualified_name: bool = False,
) -> dict[str, Any]:
    if treat_as_qualified_name:
        snippet = run_cbm_tool(
            ctx,
            "get_code_snippet",
            {"project": project_name, "qualified_name": symbol},
        )
        return {
            "name": snippet.get("name"),
            "qualified_name": snippet.get("qualified_name", symbol),
            "label": snippet.get("label", "Function"),
            "file_path": snippet.get("file_path"),
            "start_line": snippet.get("start_line"),
            "end_line": snippet.get("end_line"),
        }

    exact = run_cbm_tool(
        ctx,
        "search_graph",
        {
            "project": project_name,
            "name_pattern": f"^{re.escape(symbol)}$",
        },
    )
    exact_results = [
        item for item in exact.get("results", []) if item.get("label") in FUNCTION_LABELS
    ]
    if len(exact_results) == 1:
        return exact_results[0]
    if len(exact_results) > 1:
        items = "\n".join(
            f"- {item['qualified_name']} ({item.get('file_path', '?')})"
            for item in exact_results[:20]
        )
        raise ToolError(
            "symbol name is ambiguous. Use `--qualified-name` or pick a unique symbol:\n"
            f"{items}"
        )

    fuzzy = search_functions(ctx, project_name, symbol)
    fuzzy_results = fuzzy.get("results", [])
    if len(fuzzy_results) == 1:
        return fuzzy_results[0]
    if not fuzzy_results:
        raise ToolError(f"no function or method matched {symbol!r}")
    items = "\n".join(
        f"- {item['qualified_name']} ({item.get('file_path', '?')})"
        for item in fuzzy_results[:20]
    )
    raise ToolError(
        "no exact symbol matched. Closest results:\n"
        f"{items}"
    )


def query_calls(
    ctx: RepoContext,
    project_name: str,
    qualified_name: str,
    *,
    direction: str,
    depth: int,
) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, dict[str, dict[str, Any]]] = {
        "callers": {},
        "callees": {},
    }

    if direction in {"inbound", "both"}:
        for hop in range(1, depth + 1):
            query = (
                "MATCH (m)-[:CALLS*"
                f"{hop}..{hop}"
                f"]->(n {{qualified_name: {json.dumps(qualified_name)}}}) "
                "RETURN m.name AS name, m.qualified_name AS qualified_name"
            )
            payload = run_cbm_tool(
                ctx,
                "query_graph",
                {"project": project_name, "query": query},
            )
            for row in payload.get("rows", []):
                name, qn = row[0], row[1]
                results["callers"].setdefault(
                    qn,
                    {"name": name, "qualified_name": qn, "hop": hop},
                )

    if direction in {"outbound", "both"}:
        for hop in range(1, depth + 1):
            query = (
                "MATCH (n {qualified_name: "
                f"{json.dumps(qualified_name)}"
                f"}})-[:CALLS*{hop}..{hop}]->(m) "
                "RETURN m.name AS name, m.qualified_name AS qualified_name"
            )
            payload = run_cbm_tool(
                ctx,
                "query_graph",
                {"project": project_name, "query": query},
            )
            for row in payload.get("rows", []):
                name, qn = row[0], row[1]
                results["callees"].setdefault(
                    qn,
                    {"name": name, "qualified_name": qn, "hop": hop},
                )

    return {
        "callers": sorted(results["callers"].values(), key=lambda item: (item["hop"], item["qualified_name"])),
        "callees": sorted(results["callees"].values(), key=lambda item: (item["hop"], item["qualified_name"])),
    }


def format_search_results(results: list[dict[str, Any]], *, limit: int) -> str:
    if not results:
        return "No matching functions."

    lines: list[str] = []
    for item in results[:limit]:
        location = item.get("file_path", "?")
        if item.get("start_line"):
            location = f"{location}:{item['start_line']}"
        lines.append(f"{item.get('name', '?')} [{item.get('label', '?')}] {location}")
        if item.get("qualified_name"):
            lines.append(f"  {item['qualified_name']}")
    if len(results) > limit:
        lines.append(f"... {len(results) - limit} more result(s)")
    return "\n".join(lines)


def format_code_search_results(payload: dict[str, Any], *, limit: int) -> str:
    results = payload.get("results", [])
    if not results:
        return "No code matches."

    lines: list[str] = []
    for item in results[:limit]:
        location = item.get("file", "?")
        if item.get("start_line"):
            location = f"{location}:{item['start_line']}"
        lines.append(f"{item.get('node', '?')} [{item.get('label', '?')}] {location}")
        if item.get("qualified_name"):
            lines.append(f"  {item['qualified_name']}")
        if item.get("match_lines"):
            lines.append(f"  match_lines={','.join(str(v) for v in item['match_lines'])}")
    if len(results) > limit:
        lines.append(f"... {len(results) - limit} more result(s)")
    return "\n".join(lines)


def format_calls(symbol: dict[str, Any], calls: dict[str, list[dict[str, Any]]], direction: str) -> str:
    lines = [f"Resolved: {symbol['qualified_name']}", f"Direction: {direction}"]
    lines.append("Callers:")
    if calls["callers"]:
        for item in calls["callers"]:
            lines.append(f"  - {item['name']} (hop={item['hop']}) {item['qualified_name']}")
    else:
        lines.append("  - none")

    lines.append("Callees:")
    if calls["callees"]:
        for item in calls["callees"]:
            lines.append(f"  - {item['name']} (hop={item['hop']}) {item['qualified_name']}")
    else:
        lines.append("  - none")
    return "\n".join(lines)


def format_query_rows(payload: dict[str, Any]) -> str:
    columns = payload.get("columns", [])
    rows = payload.get("rows", [])
    if not rows:
        return "No rows."
    lines = ["\t".join(str(column) for column in columns)]
    for row in rows:
        lines.append("\t".join(str(cell) for cell in row))
    return "\n".join(lines)


def format_detect_changes(payload: dict[str, Any]) -> str:
    lines = [
        f"Changed files: {payload.get('changed_count', 0)}",
        f"Impacted symbols: {len(payload.get('impacted_symbols', []))}",
    ]
    for path in payload.get("changed_files", []):
        lines.append(f"  - {path}")
    for symbol in payload.get("impacted_symbols", []):
        if isinstance(symbol, dict):
            lines.append(
                f"  * {symbol.get('qualified_name') or symbol.get('name') or symbol}"
            )
        else:
            lines.append(f"  * {symbol}")
    return "\n".join(lines)


def format_projects(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return "No indexed projects."
    lines: list[str] = []
    for item in projects:
        lines.append(
            f"{item.get('name')} nodes={item.get('nodes')} edges={item.get('edges')} "
            f"root={item.get('root_path')}"
        )
    return "\n".join(lines)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def command_status(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    payload: dict[str, Any] = {
        "repo_root": str(ctx.repo_root),
        "tool_dir": str(ctx.tool_dir),
        "cache_dir": str(ctx.cache_dir),
        "db_files": [path.name for path in indexed_db_files(ctx)],
        "head_commit": git_head_commit(ctx.repo_root),
        "repo_dirty": repo_has_non_tool_changes(ctx.repo_root),
    }
    metadata = load_metadata(ctx)
    if metadata:
        payload["metadata"] = metadata
    try:
        payload["project_name"] = resolve_project_name(ctx)
        payload["index_status"] = run_cbm_tool(
            ctx,
            "index_status",
            {"project": payload["project_name"]},
        )
    except ToolError:
        pass

    if args.json:
        print_json(payload)
    else:
        print(f"Repo root: {ctx.repo_root}")
        print(f"Tool dir: {ctx.tool_dir}")
        print(f"Cache dir: {ctx.cache_dir}")
        print(f"DB files: {', '.join(payload['db_files']) or 'none'}")
        if payload.get("project_name"):
            print(f"Project name: {payload['project_name']}")
        if payload.get("index_status"):
            print(f"Index status: {payload['index_status'].get('status')}")
            print(
                f"Nodes/Edges: {payload['index_status'].get('nodes')} / "
                f"{payload['index_status'].get('edges')}"
            )
        if payload.get("metadata"):
            print(f"Last index: {payload['metadata'].get('indexed_at')}")
            print(f"Mode: {payload['metadata'].get('mode')}")
    return 0


def command_index(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    payload = perform_index(ctx, mode=args.mode, clean=args.clean)
    if args.json:
        print_json(payload)
    else:
        print(f"Indexed: {ctx.repo_root}")
        print(f"Mode: {args.mode}")
        print(f"Project name: {payload['project_name']}")
        print(f"Cache dir: {ctx.cache_dir}")
    return 0


def command_projects(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    projects = list_projects(ctx)
    if args.json:
        print_json({"projects": projects})
    else:
        print(format_projects(projects))
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    metadata = load_metadata(ctx)
    mode = resolve_index_mode(ctx, args.mode)
    reason = "forced" if args.force else determine_refresh_reason(
        has_db=bool(indexed_db_files(ctx)),
        metadata=metadata,
        current_head=git_head_commit(ctx.repo_root),
        repo_dirty=repo_has_non_tool_changes(ctx.repo_root),
        requested_mode=args.mode,
    )

    if reason is None:
        payload = {
            "status": "up_to_date",
            "mode": mode,
            "project_name": metadata.get("project_name") if metadata else None,
            "head_commit": git_head_commit(ctx.repo_root),
        }
        if args.json:
            print_json(payload)
        else:
            print("Index is already up to date.")
            if payload["project_name"]:
                print(f"Project name: {payload['project_name']}")
            print(f"Mode: {mode}")
        return 0

    payload = perform_index(ctx, mode=mode, clean=args.clean)
    payload["refresh_reason"] = reason
    if args.json:
        print_json(payload)
    else:
        print(f"Refreshed index: {ctx.repo_root}")
        print(f"Reason: {reason}")
        print(f"Mode: {mode}")
        print(f"Project name: {payload['project_name']}")
    return 0


def command_reset(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    if ctx.cache_dir.exists():
        try:
            project_name = resolve_project_name(ctx)
            run_cbm_tool(ctx, "delete_project", {"project": project_name})
        except ToolError:
            pass
    for path in [ctx.tool_dir, ctx.legacy_tool_dir]:
        if path.exists():
            shutil.rmtree(path)
    if args.json:
        print_json({"status": "deleted", "tool_dir": str(ctx.tool_dir)})
    else:
        print(f"Deleted local index: {ctx.tool_dir}")
    return 0


def command_self_check(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "tool_name": APP_NAME,
        "tool_version": VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_in_path": bool(shutil.which("git")),
        "python3_in_path": bool(shutil.which("python3")),
        "codebase_command_in_path": bool(shutil.which("codebase")),
    }
    try:
        payload["cbm_runner"] = resolve_cbm_runner()
    except ToolError as exc:
        payload["cbm_runner_error"] = str(exc)

    try:
        ctx = active_repo_context()
        payload["inside_git_repo"] = True
        payload["repo_root"] = str(ctx.repo_root)
        payload["repo_dirty"] = repo_has_non_tool_changes(ctx.repo_root)
        payload["head_commit"] = git_head_commit(ctx.repo_root)
        payload["index_exists"] = bool(indexed_db_files(ctx))
        payload["metadata_exists"] = bool(load_metadata(ctx))
        if payload["index_exists"]:
            payload["project_name"] = resolve_project_name(ctx)
    except ToolError as exc:
        payload["inside_git_repo"] = False
        payload["repo_error"] = str(exc)

    if args.json:
        print_json(payload)
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0


def command_func(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    search = search_functions(ctx, project_name, args.keyword, use_regex=args.regex)
    results = search.get("results", [])
    if args.json:
        print_json(
            {
                "project_name": project_name,
                "total": search.get("total", len(results)),
                "results": results[: args.limit],
            }
        )
    else:
        print(format_search_results(results, limit=args.limit))
    return 0


def command_calls(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    symbol = resolve_symbol(
        ctx,
        project_name,
        args.symbol,
        treat_as_qualified_name=args.qualified_name,
    )
    calls = query_calls(
        ctx,
        project_name,
        symbol["qualified_name"],
        direction=args.direction,
        depth=args.depth,
    )
    payload = {"resolved_symbol": symbol, "direction": args.direction, **calls}
    if args.json:
        print_json(payload)
    else:
        print(format_calls(symbol, calls, args.direction))
    return 0


def command_snippet(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    symbol = resolve_symbol(
        ctx,
        project_name,
        args.symbol,
        treat_as_qualified_name=args.qualified_name,
    )
    snippet = run_cbm_tool(
        ctx,
        "get_code_snippet",
        {"project": project_name, "qualified_name": symbol["qualified_name"]},
    )
    if args.json:
        print_json(snippet)
    else:
        print(f"{snippet.get('qualified_name')} {snippet.get('file_path')}:{snippet.get('start_line')}")
        print(snippet.get("source", "").rstrip())
    return 0


def command_search_graph(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    payload: dict[str, Any] = {"project": project_name}
    if args.term:
        payload["query"] = args.term
    if args.label:
        payload["label"] = args.label
    if args.name_pattern:
        payload["name_pattern"] = args.name_pattern
    if args.qn_pattern:
        payload["qn_pattern"] = args.qn_pattern

    response = run_cbm_tool(ctx, "search_graph", payload)
    results = response.get("results", [])
    if args.json:
        print_json(response)
    else:
        print(format_search_results(results, limit=args.limit))
    return 0


def command_trace_path(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    payload: dict[str, Any] = {
        "project": project_name,
        "function_name": args.function_name,
        "direction": args.direction,
        "depth": args.depth,
        "mode": args.mode,
        "include_tests": args.include_tests,
    }
    if args.parameter_name:
        payload["parameter_name"] = args.parameter_name
    response = run_cbm_tool(ctx, "trace_path", payload)
    print_json(response)
    return 0


def command_search_code(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    payload: dict[str, Any] = {
        "project": project_name,
        "pattern": args.pattern,
        "mode": args.mode,
        "limit": args.limit,
    }
    if args.regex:
        payload["regex"] = True
    if args.file_pattern:
        payload["file_pattern"] = args.file_pattern
    if args.path_filter:
        payload["path_filter"] = args.path_filter
    if args.context is not None:
        payload["context"] = args.context

    response = run_cbm_tool(ctx, "search_code", payload)
    if args.json:
        print_json(response)
    else:
        print(format_code_search_results(response, limit=args.limit))
    return 0


def command_query_graph(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    payload: dict[str, Any] = {"project": project_name, "query": args.query}
    if args.max_rows is not None:
        payload["max_rows"] = args.max_rows
    response = run_cbm_tool(ctx, "query_graph", payload)
    if args.json:
        print_json(response)
    else:
        print(format_query_rows(response))
    return 0


def command_detect_changes(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    payload: dict[str, Any] = {
        "project": project_name,
        "scope": args.scope,
        "depth": args.depth,
        "base_branch": args.base_branch,
    }
    if args.since:
        payload["since"] = args.since
    response = run_cbm_tool(ctx, "detect_changes", payload)
    if args.json:
        print_json(response)
    else:
        print(format_detect_changes(response))
    return 0


def command_architecture(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    payload = {
        "project": project_name,
        "aspects": args.aspects or ["all"],
    }
    response = run_cbm_tool(ctx, "get_architecture", payload)
    print_json(response)
    return 0


def command_schema(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    response = run_cbm_tool(ctx, "get_graph_schema", {"project": project_name})
    print_json(response)
    return 0


def command_index_status(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    response = run_cbm_tool(ctx, "index_status", {"project": project_name})
    if args.json:
        print_json(response)
    else:
        print(
            f"Project: {response.get('project')}\n"
            f"Status: {response.get('status')}\n"
            f"Nodes: {response.get('nodes')}\n"
            f"Edges: {response.get('edges')}"
        )
    return 0


def command_adr(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    payload: dict[str, Any] = {"project": project_name, "mode": args.mode}
    if args.mode == "update":
        content = args.content
        if args.file:
            content = Path(args.file).read_text(encoding="utf-8")
        if not content:
            raise ToolError("`adr update` requires --content or --file")
        payload["content"] = content
    if args.mode == "sections":
        if args.sections:
            payload["sections"] = args.sections
    response = run_cbm_tool(ctx, "manage_adr", payload)
    print_json(response)
    return 0


def command_ingest_traces(args: argparse.Namespace) -> int:
    ctx = active_repo_context()
    project_name = ensure_project_name(ctx)
    trace_path = Path(args.file)
    raw = json.loads(trace_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        traces = raw
    elif isinstance(raw, dict) and isinstance(raw.get("traces"), list):
        traces = raw["traces"]
    else:
        raise ToolError("trace file must be a JSON array or an object with a `traces` array")
    response = run_cbm_tool(
        ctx,
        "ingest_traces",
        {"project": project_name, "traces": traces},
    )
    print_json(response)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Local repository-scoped wrapper around codebase-memory-mcp.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Commands:
              status                Show local index state under .codebase
              index                 Build or rebuild the local index
              refresh               Rebuild only when the repo or mode changed
              projects              List indexed projects in current local cache
              reset                 Delete the local .codebase index
              self-check            Verify environment, repo, and tool wiring
              func <keyword>        Search functions and methods
              calls <symbol>        Show callers/callees for one resolved symbol
              snippet <symbol>      Show source for one resolved symbol
              search-graph          Direct wrapper for search_graph
              trace-path            Direct wrapper for trace_path
              search-code           Text/code search via search_code
              query-graph           Run a graph query
              detect-changes        Inspect changed files and impacted symbols
              architecture          Get architecture summary
              schema                Get graph schema summary
              index-status          Get current index status
              adr                   Manage local ADR content
              ingest-traces         Ingest runtime traces from a JSON file
            """
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show local index status")
    status.add_argument("--json", action="store_true", help="print JSON")
    status.set_defaults(func=command_status)

    index = subparsers.add_parser("index", help="build the local index under .codebase")
    index.add_argument(
        "--mode",
        choices=["full", "moderate", "fast"],
        default="full",
        help="indexing depth",
    )
    index.add_argument("--clean", action="store_true", help="remove existing .codebase before indexing")
    index.add_argument("--json", action="store_true", help="print JSON")
    index.set_defaults(func=command_index)

    refresh = subparsers.add_parser("refresh", help="rebuild only when local index is stale")
    refresh.add_argument(
        "--mode",
        choices=["full", "moderate", "fast"],
        help="override index mode; if omitted, reuse metadata mode or default to full",
    )
    refresh.add_argument("--force", action="store_true", help="refresh even if already up to date")
    refresh.add_argument("--clean", action="store_true", help="remove existing .codebase before refreshing")
    refresh.add_argument("--json", action="store_true", help="print JSON")
    refresh.set_defaults(func=command_refresh)

    projects = subparsers.add_parser("projects", help="list indexed projects in local cache")
    projects.add_argument("--json", action="store_true", help="print JSON")
    projects.set_defaults(func=command_projects)

    reset = subparsers.add_parser("reset", help="delete local .codebase index")
    reset.add_argument("--json", action="store_true", help="print JSON")
    reset.set_defaults(func=command_reset)

    self_check = subparsers.add_parser("self-check", help="verify environment and repo wiring")
    self_check.add_argument("--json", action="store_true", help="print JSON")
    self_check.set_defaults(func=command_self_check)

    func = subparsers.add_parser("func", help="search indexed functions and methods")
    func.add_argument("keyword", help="keyword or regex")
    func.add_argument("--regex", action="store_true", help="treat keyword as search_graph name_pattern")
    func.add_argument("--limit", type=int, default=20, help="maximum displayed results")
    func.add_argument("--json", action="store_true", help="print JSON")
    func.set_defaults(func=command_func)

    calls = subparsers.add_parser("calls", help="show callers and callees for a symbol")
    calls.add_argument("symbol", help="symbol name or qualified_name")
    calls.add_argument("--qualified-name", action="store_true", help="treat symbol as exact qualified_name")
    calls.add_argument(
        "--direction",
        choices=["inbound", "outbound", "both"],
        default="both",
        help="graph direction",
    )
    calls.add_argument("--depth", type=int, default=3, help="maximum call depth")
    calls.add_argument("--json", action="store_true", help="print JSON")
    calls.set_defaults(func=command_calls)

    snippet = subparsers.add_parser("snippet", help="show source for a symbol")
    snippet.add_argument("symbol", help="symbol name or qualified_name")
    snippet.add_argument("--qualified-name", action="store_true", help="treat symbol as exact qualified_name")
    snippet.add_argument("--json", action="store_true", help="print JSON")
    snippet.set_defaults(func=command_snippet)

    search_graph = subparsers.add_parser("search-graph", help="direct wrapper around search_graph")
    search_graph.add_argument("term", nargs="?", help="bm25 keyword query")
    search_graph.add_argument("--label", help="optional node label filter")
    search_graph.add_argument("--name-pattern", help="regex for node name")
    search_graph.add_argument("--qn-pattern", help="regex for qualified_name")
    search_graph.add_argument("--limit", type=int, default=20, help="maximum displayed results")
    search_graph.add_argument("--json", action="store_true", help="print JSON")
    search_graph.set_defaults(func=command_search_graph)

    trace_path = subparsers.add_parser("trace-path", help="direct wrapper around trace_path")
    trace_path.add_argument("function_name", help="short function name for upstream trace_path")
    trace_path.add_argument(
        "--direction",
        choices=["inbound", "outbound", "both"],
        default="both",
        help="graph direction",
    )
    trace_path.add_argument("--depth", type=int, default=3, help="maximum path depth")
    trace_path.add_argument(
        "--mode",
        choices=["calls", "data_flow", "cross_service"],
        default="calls",
        help="trace mode",
    )
    trace_path.add_argument("--parameter-name", help="parameter name for data_flow mode")
    trace_path.add_argument("--include-tests", action="store_true", help="include test files")
    trace_path.add_argument("--json", action="store_true", help="print JSON")
    trace_path.set_defaults(func=command_trace_path)

    search_code = subparsers.add_parser("search-code", help="text/code search with graph-aware ranking")
    search_code.add_argument("pattern", help="text or regex pattern")
    search_code.add_argument("--mode", choices=["compact", "full", "files"], default="compact")
    search_code.add_argument("--file-pattern", help="glob include, for example *.py")
    search_code.add_argument("--path-filter", help="regex filter on result paths")
    search_code.add_argument("--context", type=int, help="context lines in compact mode")
    search_code.add_argument("--regex", action="store_true", help="treat pattern as regex")
    search_code.add_argument("--limit", type=int, default=10, help="maximum results")
    search_code.add_argument("--json", action="store_true", help="print JSON")
    search_code.set_defaults(func=command_search_code)

    query_graph = subparsers.add_parser("query-graph", help="run a graph query directly")
    query_graph.add_argument("query", help="query string")
    query_graph.add_argument("--max-rows", type=int, help="optional maximum rows")
    query_graph.add_argument("--json", action="store_true", help="print JSON")
    query_graph.set_defaults(func=command_query_graph)

    detect_changes = subparsers.add_parser("detect-changes", help="show changed files and impacted symbols")
    detect_changes.add_argument(
        "--scope",
        default="working_tree",
        help="scope passed to upstream detect_changes",
    )
    detect_changes.add_argument("--depth", type=int, default=2, help="impact depth")
    detect_changes.add_argument("--base-branch", default="main", help="base branch")
    detect_changes.add_argument("--since", help="git ref or date")
    detect_changes.add_argument("--json", action="store_true", help="print JSON")
    detect_changes.set_defaults(func=command_detect_changes)

    architecture = subparsers.add_parser("architecture", help="get architecture summary")
    architecture.add_argument("aspects", nargs="*", help="architecture aspects, default is all")
    architecture.add_argument("--json", action="store_true", help="print JSON")
    architecture.set_defaults(func=command_architecture)

    schema = subparsers.add_parser("schema", help="get graph schema summary")
    schema.add_argument("--json", action="store_true", help="print JSON")
    schema.set_defaults(func=command_schema)

    index_status = subparsers.add_parser("index-status", help="get upstream index status")
    index_status.add_argument("--json", action="store_true", help="print JSON")
    index_status.set_defaults(func=command_index_status)

    adr = subparsers.add_parser("adr", help="manage ADR content via upstream manage_adr")
    adr.add_argument("mode", choices=["get", "update", "sections"], help="ADR mode")
    adr.add_argument("--content", help="ADR content for update")
    adr.add_argument("--file", help="read ADR content from file for update")
    adr.add_argument("sections", nargs="*", help="section names for `sections` mode")
    adr.add_argument("--json", action="store_true", help="print JSON")
    adr.set_defaults(func=command_adr)

    ingest_traces = subparsers.add_parser("ingest-traces", help="ingest runtime traces from a JSON file")
    ingest_traces.add_argument("file", help="JSON file path containing traces")
    ingest_traces.add_argument("--json", action="store_true", help="print JSON")
    ingest_traces.set_defaults(func=command_ingest_traces)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ToolError as exc:
        print(f"{APP_NAME}: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"{APP_NAME}: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
