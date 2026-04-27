from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from codebase_cli import cli as MODULE


class CodebaseHelpersTest(unittest.TestCase):
    def test_detect_repo_context_uses_cwd(self) -> None:
        fake_root = Path("/tmp/example-project").resolve()
        with mock.patch.object(MODULE, "resolve_session_context", return_value=("test-uuid", "flag")):
            ctx = MODULE.detect_repo_context(cwd=fake_root)
        self.assertEqual(ctx.repo_root, fake_root)
        self.assertEqual(ctx.root_dir, fake_root / ".codebase")
        self.assertEqual(ctx.session_name, "test-uuid")
        self.assertEqual(ctx.session_dir, fake_root / ".codebase" / "test-uuid")
        self.assertEqual(ctx.cache_dir, fake_root / ".codebase" / "test-uuid" / "index")

    def test_detect_repo_context_defaults_to_cwd(self) -> None:
        ctx = MODULE.detect_repo_context()
        self.assertEqual(ctx.repo_root, Path.cwd().resolve())

    def test_refresh_reason_missing_index(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=False,
            metadata=None,
        )
        self.assertEqual(reason, "missing_index")

    def test_refresh_reason_missing_metadata(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=True,
            metadata=None,
        )
        self.assertEqual(reason, "missing_metadata")

    def test_refresh_reason_mode_changed(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=True,
            metadata={"mode": "fast"},
            requested_mode="full",
        )
        self.assertEqual(reason, "mode_changed")

    def test_refresh_reason_none_when_current(self) -> None:
        reason = MODULE.determine_refresh_reason(
            has_db=True,
            metadata={"mode": "full"},
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

    def test_extract_uuid_from_command(self) -> None:
        self.assertEqual(
            MODULE.extract_uuid_from_command("claude --resume d0f7ca83-c52c-450e-8cc0-4f4f2f3313b8"),
            "d0f7ca83-c52c-450e-8cc0-4f4f2f3313b8",
        )
        self.assertEqual(
            MODULE.extract_uuid_from_command("codex resume 019da154-2915-7413-852c-230622b512f4"),
            "019da154-2915-7413-852c-230622b512f4",
        )
        self.assertIsNone(MODULE.extract_uuid_from_command("python3 -m codebase_cli index"))

    def test_resolve_session_context_flag_override(self) -> None:
        name, source = MODULE.resolve_session_context(session_override="my-session-id")
        self.assertEqual(name, "my-session-id")
        self.assertEqual(source, "flag")

    def test_resolve_session_context_env_override(self) -> None:
        with mock.patch.dict("os.environ", {"CODEBASE_SESSION": "env-session-id"}):
            name, source = MODULE.resolve_session_context()
        self.assertEqual(name, "env-session-id")
        self.assertEqual(source, "env:CODEBASE_SESSION")


if __name__ == "__main__":
    unittest.main()
