from __future__ import annotations

from pathlib import Path
import sys
import unittest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from codebase_cli import cli as MODULE


class CodebaseHelpersTest(unittest.TestCase):
    def test_parse_status_path_for_rename(self) -> None:
        self.assertEqual(
            MODULE.parse_status_path("R  old/path.py -> new/path.py"),
            "new/path.py",
        )

    def test_codex_work_path_detection(self) -> None:
        self.assertTrue(MODULE.is_codex_work_path(".codex"))
        self.assertTrue(MODULE.is_codex_work_path(".codex/cbm/index.db"))
        self.assertFalse(MODULE.is_codex_work_path("src/app.py"))

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


if __name__ == "__main__":
    unittest.main()
