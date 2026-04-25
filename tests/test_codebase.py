from __future__ import annotations

from pathlib import Path
import sys
import tempfile
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

    def test_tool_work_path_detection(self) -> None:
        self.assertTrue(MODULE.is_tool_work_path(".codebase"))
        self.assertTrue(MODULE.is_tool_work_path(".codebase/index/index.db"))
        self.assertTrue(MODULE.is_tool_work_path(".codex/cbm/index.db"))
        self.assertFalse(MODULE.is_tool_work_path("src/app.py"))

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

    def test_migrate_legacy_layout_moves_codex_data_to_codebase(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            legacy_tool_dir = repo_root / ".codex" / "cbm"
            legacy_cache_dir = legacy_tool_dir / "index"
            legacy_cache_dir.mkdir(parents=True)
            (legacy_cache_dir / "graph.db").write_text("db", encoding="utf-8")
            (legacy_tool_dir / "metadata.json").write_text("{}", encoding="utf-8")

            ctx = MODULE.RepoContext(
                repo_root=repo_root,
                tool_dir=repo_root / ".codebase",
                cache_dir=repo_root / ".codebase" / "index",
                metadata_path=repo_root / ".codebase" / "metadata.json",
                legacy_tool_dir=legacy_tool_dir,
                legacy_cache_dir=legacy_cache_dir,
                legacy_metadata_path=legacy_tool_dir / "metadata.json",
            )

            migrated = MODULE.migrate_legacy_layout(ctx)

            self.assertTrue(migrated)
            self.assertTrue((repo_root / ".codebase" / "index" / "graph.db").exists())
            self.assertTrue((repo_root / ".codebase" / "metadata.json").exists())
            self.assertFalse(legacy_tool_dir.exists())


if __name__ == "__main__":
    unittest.main()
