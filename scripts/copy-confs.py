#!/usr/bin/env python3

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from lib import get_curseforge_instance_dir


CONFIG_COPIES = [
  {
    "name": "FTB Quests",
    "relative_path": Path("ftbquests"),
    "path_type": "directory",
  },
  {
    "name": "Structurify",
    "relative_path": Path("structurify.json"),
    "path_type": "file",
  },
]


def fail(message: str) -> None:
  print(message, file=sys.stderr)
  raise SystemExit(1)


def refuse_unsafe_destination(path: Path) -> None:
  resolved = path.resolve(strict=False)

  if resolved == Path(resolved.anchor):
    fail(f"Refusing to overwrite filesystem root as destination: {resolved}")


def remove_existing_destination(path: Path) -> None:
  if not path.exists() and not path.is_symlink():
    return

  if path.is_dir() and not path.is_symlink():
    shutil.rmtree(path)
  else:
    path.unlink()


def copy_config(
  *,
  name: str,
  relative_path: Path,
  path_type: str,
  instance_dir: Path,
  destination_parent: Path,
) -> None:
  source = instance_dir / "config" / relative_path
  destination = destination_parent / relative_path

  if path_type == "directory":
    if not source.is_dir():
      fail(f"{name} source not found: {source}")
  elif path_type == "file":
    if not source.is_file():
      fail(f"{name} source not found: {source}")
  else:
    fail(f"Invalid path type for {name}: {path_type}")

  refuse_unsafe_destination(destination)

  print(f"{name}:")
  print(f"  Source: {source}")
  print(f"  Destination: {destination}")

  if path_type == "directory":
    remove_existing_destination(destination)
    shutil.copytree(source, destination)
  else:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

  print()


def main() -> int:
  try:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    destination_parent = repo_root / "pack-configs" / "config"
    instance_dir = get_curseforge_instance_dir()

    print("======================================")
    print("Copy Configs Into Repo")
    print("======================================")

    destination_parent.mkdir(parents=True, exist_ok=True)

    for config_copy in CONFIG_COPIES:
      copy_config(
        name=config_copy["name"],
        relative_path=config_copy["relative_path"],
        path_type=config_copy["path_type"],
        instance_dir=instance_dir,
        destination_parent=destination_parent,
      )

    print("Configs copied into pack-configs/config.")
  except (OSError, ValueError) as exc:
    print(exc, file=sys.stderr)
    return 1

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
