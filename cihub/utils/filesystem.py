"""Filesystem abstraction for testing and IO isolation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class FileSystem(ABC):
    """Minimal filesystem interface for read/write/exists operations."""

    @abstractmethod
    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        """Read text from a path."""

    @abstractmethod
    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text to a path, overwriting existing content."""

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Return True if the path exists."""

    def append_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        """Append text to a path, creating the file if needed."""
        existing = self.read_text(path, encoding=encoding) if self.exists(path) else ""
        self.write_text(path, existing + content, encoding=encoding)


class RealFileSystem(FileSystem):
    """Filesystem backed by the real disk."""

    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        return path.read_text(encoding=encoding)

    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        path.write_text(content, encoding=encoding)

    def exists(self, path: Path) -> bool:
        return path.exists()

    def append_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        with path.open("a", encoding=encoding) as handle:
            handle.write(content)


class MemoryFileSystem(FileSystem):
    """In-memory filesystem for tests that should not touch disk."""

    def __init__(self) -> None:
        self._files: dict[Path, str] = {}

    def read_text(self, path: Path, encoding: str = "utf-8") -> str:
        key = self._normalize(path)
        if key not in self._files:
            raise FileNotFoundError(str(path))
        return self._files[key]

    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        self._files[self._normalize(path)] = content

    def exists(self, path: Path) -> bool:
        return self._normalize(path) in self._files

    def append_text(self, path: Path, content: str, encoding: str = "utf-8") -> None:
        key = self._normalize(path)
        self._files[key] = self._files.get(key, "") + content

    @staticmethod
    def _normalize(path: Path) -> Path:
        return Path(path)
