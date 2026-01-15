"""Tests for cihub.utils.fs module."""

from __future__ import annotations

from pathlib import Path

from cihub.utils.fs import write_text


class TestWriteText:
    """Tests for write_text function."""

    def test_dry_run_with_emit(self, capsys: object, tmp_path: Path) -> None:
        """Dry run with emit prints content."""
        target = tmp_path / "test.txt"
        write_text(target, "hello world", dry_run=True, emit=True)
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert f"# Would write: {target}" in captured.out
        assert "hello world" in captured.out
        assert not target.exists()

    def test_dry_run_without_emit(self, tmp_path: Path) -> None:
        """Dry run without emit does nothing."""
        target = tmp_path / "test.txt"
        write_text(target, "hello world", dry_run=True, emit=False)
        assert not target.exists()

    def test_actual_write(self, tmp_path: Path) -> None:
        """Non-dry run writes file."""
        target = tmp_path / "subdir" / "test.txt"
        write_text(target, "hello world", dry_run=False)
        assert target.exists()
        assert target.read_text() == "hello world"
