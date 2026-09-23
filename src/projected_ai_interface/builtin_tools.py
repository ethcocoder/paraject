"""Initial safe tools for Phase 7; no arbitrary shell execution."""
from __future__ import annotations

import os
import subprocess
import shutil
from pathlib import Path
from typing import Iterable


class PathSandbox:
    def __init__(self, roots: Iterable[str | Path]) -> None:
        self.roots = tuple(Path(root).expanduser().resolve() for root in roots)
        if not self.roots:
            raise ValueError("at least one permitted root is required")

    def resolve(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser().resolve()
        if not any(candidate == root or root in candidate.parents for root in self.roots):
            raise PermissionError("path is outside permitted filesystem roots")
        return candidate


class ConfirmationRequired(PermissionError):
    """Raised before a destructive operation without explicit confirmation."""


def list_folder(path: str, sandbox: PathSandbox) -> dict:
    folder = sandbox.resolve(path)
    if not folder.is_dir():
        raise NotADirectoryError(path)
    entries = [{"name": item.name, "type": "folder" if item.is_dir() else "file"} for item in sorted(folder.iterdir(), key=lambda item: item.name.lower())]
    return {"path": str(folder), "entries": entries}


def create_folder(path: str, sandbox: PathSandbox) -> dict:
    folder = sandbox.resolve(path)
    folder.mkdir(parents=False, exist_ok=False)
    return {"created": True, "path": str(folder)}


def open_folder(path: str, sandbox: PathSandbox) -> dict:
    folder = sandbox.resolve(path)
    if not folder.is_dir():
        raise NotADirectoryError(path)
    # The tool returns a validated intent. OS-specific launching belongs to a
    # later desktop adapter and is never generated from model shell text.
    return {"validated": True, "path": str(folder), "action": "open_folder"}


def search_files(path: str, query: str, sandbox: PathSandbox) -> dict:
    root = sandbox.resolve(path)
    if not root.is_dir():
        raise NotADirectoryError(path)
    matches = [str(item) for item in root.rglob("*") if query.lower() in item.name.lower()]
    return {"path": str(root), "query": query, "matches": matches[:100]}


def copy_file(source: str, destination: str, sandbox: PathSandbox) -> dict:
    source_path, destination_path = sandbox.resolve(source), sandbox.resolve(destination)
    if not source_path.is_file():
        raise FileNotFoundError(source)
    if destination_path.exists():
        raise FileExistsError(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    return {"copied": True, "source": str(source_path), "destination": str(destination_path)}


def move_file(source: str, destination: str, sandbox: PathSandbox) -> dict:
    source_path, destination_path = sandbox.resolve(source), sandbox.resolve(destination)
    if not source_path.is_file():
        raise FileNotFoundError(source)
    if destination_path.exists():
        raise FileExistsError(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(destination_path))
    return {"moved": True, "source": str(source_path), "destination": str(destination_path)}


def delete_file(path: str, sandbox: PathSandbox, confirmed: bool = False) -> dict:
    if not confirmed:
        raise ConfirmationRequired("delete_file requires explicit confirmation")
    target = sandbox.resolve(path)
    if not target.is_file():
        raise FileNotFoundError(path)
    target.unlink()
    return {"deleted": True, "path": str(target)}


def open_app(command: str, allowed_commands: set[str]) -> dict:
    if command not in allowed_commands:
        raise PermissionError("application is not allowlisted")
    # Explicitly do not launch here; return an approved intent for the OS adapter.
    return {"validated": True, "command": command, "action": "open_app"}
