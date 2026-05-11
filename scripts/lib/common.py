#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


def fail(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
    raise SystemExit(1)


def log(message: str, *, quiet: bool = False) -> None:
    if not quiet:
        print(message, flush=True)


def verbose_log(message: str, *, verbose: bool = False, quiet: bool = False) -> None:
    if verbose and not quiet:
        print(message, flush=True)


def is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        fail(f"Failed to read JSON from {path}: {error}")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        fail(f"Failed to write JSON to {path}: {error}")


def slugify_version(value: str) -> str:
    value = value.strip()
    if not value:
        fail("Version cannot be empty")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        fail("Version may only contain letters, numbers, dots, underscores, and hyphens")
    return value


def remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def copy_path(source: Path, destination: Path, *, ignore_patterns: list[str] | None = None) -> None:
    if not source.exists():
        fail(f"Source not found: {source}")

    remove_path(destination)

    if source.is_dir():
        if ignore_patterns:
            def ignore_func(path, names):
                import fnmatch
                return [name for name in names if any(fnmatch.fnmatchcase(name, p) for p in ignore_patterns)]
            shutil.copytree(source, destination, ignore=ignore_func)
        else:
            shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
