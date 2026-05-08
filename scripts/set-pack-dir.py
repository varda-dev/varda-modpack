#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PACK_DIR_FILE = REPO_ROOT / "PACK_DIR.txt"


def is_blank(value: str | None) -> bool:
  return value is None or value.strip() == ""


def resolve_pack_dir(raw_path: str) -> Path:
  try:
    path = Path(raw_path).expanduser()
  except RuntimeError as exc:
    raise ValueError(f"Could not expand home directory in path: {raw_path}") from exc

  if not path.is_absolute():
    path = Path.cwd() / path

  if not path.exists():
    raise FileNotFoundError(f"PACK_DIR does not exist: {path}")

  if not path.is_dir():
    raise NotADirectoryError(f"PACK_DIR is not a directory: {path}")

  return path.resolve()


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Write PACK_DIR.txt with the modpack instance folder path."
  )

  parser.add_argument(
    "pack_dir",
    nargs="?",
    help="Full path to your modpack instance folder.",
  )

  args = parser.parse_args()

  pack_dir = args.pack_dir

  if is_blank(pack_dir):
    try:
      pack_dir = input("Enter full path to your modpack instance folder: ")
    except EOFError:
      print()
      pack_dir = None

  if is_blank(pack_dir):
    print("PACK_DIR cannot be empty.", file=sys.stderr)
    return 1

  try:
    resolved_pack_dir = resolve_pack_dir(pack_dir)
    PACK_DIR_FILE.write_text(
      f"{resolved_pack_dir}\n",
      encoding="utf-8",
      newline="\n",
    )
  except (OSError, ValueError) as exc:
    print(exc, file=sys.stderr)
    return 1

  print("PACK_DIR.txt written as:")
  print(PACK_DIR_FILE.read_text(encoding="utf-8"), end="")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
