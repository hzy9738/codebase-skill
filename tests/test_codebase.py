from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from codebase_cli import cli as MODULE


class CodebaseHelpersTest(unittest.TestCase):
    def test_parse_status_path_for_rename(self) -> None:
        self.assertEqual(
            MODULE.parse_status_path("R  old/path.py -> new/path.py"),
            "new/path.py",
        )

    def test_tool_work_path_detection(self) -> None:
        self.assertTrue(MODULE.is_tool_work_path(".codebase"))
        self.assertTrue(MODULE.is_tool_work_path(".codebase/codex/index.db"))
        self.assertFalse(MODULE.is_tool_work_path("src/app.py"))

    def test_normalize_session_aliases(self) -> None:
        self.assertEqual(MODULE.normalize_session_name("codex"), "codex")
        self.assertEqual(MODULE.normalize_session_name("claude-code"), "claudecode")
        self.assertEqual(MODULE.normalize_session_name("Open Code"), "opencode")
        self.assertEqual(MODULE.normalize_session_name(""), "default")

    def test_detect_session_from_command(self) -> None:
        self.assertEqual(
            MODULE.detect_session_from_command("/Users/example/.nvm/bin/codex"),
            "codex",
        )
        self.assertEqual(
            MODULE.detect_session_from_command("node /opt/tools/claude"),
            "claudecode",
        )
        self.assertEqual(
            MODULE.detect_session_from_command("/opt/homebrew/bin/opencode --run"),
            "opencode",
        )

    def test_detect_repo_context_uses_session_namespace(self) -> None:
        fake_repo = Path("/tmp/example-repo").resolve()
        with mock.patch.object(MODULE, "git_output", return_value=str(fake_repo)):
            ctx = MODULE.detect_repo_context(session="claude-code")
        self.assertEqual(ctx.repo_root, fake_repo)
        self.assertEqual(ctx.root_dir, fake_repo / ".codebase")
        self.assertEqual(ctx.session_name, "claudecode")
        self.assertEqual(ctx.session_dir, fake_repo / ".codebase" / "claudecode")
        self.assertEqual(ctx.cache_dir, fake_repo / ".codebase" / "claudecode" / "index")

    def test_refresh_reason_missing_index(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=False,
            metadata=None,
            current_head="abc",
            repo_dirty=False,
        )
        self.assertEqual(reason, "missing_index")

    def test_refresh_reason_dirty_worktree(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=True,
            metadata={"mode": "full", "head_commit": "abc"},
            current_head="abc",
            repo_dirty=True,
        )
        self.assertEqual(reason, "dirty_worktree")

    def test_refresh_reason_head_changed(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=True,
            metadata={"mode": "full", "head_commit": "abc"},
            current_head="def",
            repo_dirty=False,
        )
        self.assertEqual(reason, "head_changed")

    def test_refresh_reason_mode_changed(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=True,
            metadata={"mode": "fast", "head_commit": "abc"},
            current_head="abc",
            repo_dirty=False,
            requested_mode="full",
        )
        self.assertEqual(reason, "mode_changed")

    def test_refresh_reason_none_when_current(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=True,
            metadata={"mode": "full", "head_commit": "abc"},
            current_head="abc",
            repo_dirty=False,
        )
        self.assertIsNone(reason)

    def test_resolve_index_mode_prefers_metadata(self) -> None:
        class DummyContext:
            metadata_path = Path("/tmp/nonexistent-metadata.json")

        original = MODULE.load_metadata
        try:
            MODULE.load_metadata = lambda ctx: {"mode": "moderate"}
            self.assertEqual(MODULE.resolve_index_mode(DummyContext()), "moderate")
        finally:
            MODULE.load_metadata = original

    def test_current_platform_slug(self) -> None:
        with mock.patch.object(MODULE.platform, "system", return_value="Darwin"):
            with mock.patch.object(MODULE.platform, "machine", return_value="arm64"):
                self.assertEqual(MODULE.current_platform_slug(), "darwin-arm64")


if __name__ == "__main__":
    unittest.main()
