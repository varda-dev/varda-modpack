#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.common import fail, copy_path as lib_copy_path
from lib.env import get_curseforge_instance_dir


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


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Copy specific config files from the Minecraft instance into the repository."
  )
  return parser.parse_args()


def main() -> int:
  args = parse_args()
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
      name = config_copy["name"]
      relative_path = config_copy["relative_path"]
      path_type = config_copy["path_type"]
      
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

      print(f"{name}:")
      print(f"  Source: {source}")
      print(f"  Destination: {destination}")

      lib_copy_path(source, destination)
      print()

    print("Configs copied into pack-configs/config.")
  except (OSError, ValueError) as exc:
    print(exc, file=sys.stderr)
    return 1

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
