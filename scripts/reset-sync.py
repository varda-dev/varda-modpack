#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from lib.common import fail, is_blank, remove_path, copy_path as lib_copy_path
from lib.env import get_curseforge_instance_dir


FULL_WIPE_FOLDERS = [
  ".mixin.out",
  ".mtsession",
  "backups",
  "config",
  "crash-reports",
  "defaultconfigs",
  "downloads",
  "dynamic-data-pack-cache",
  "dynamic-resource-pack-cache",
  "ESM",
  "ftbbackups3",
  "kubejs",
  "local",
  "logs",
  "moonlight-global-datapacks",
  "patchouli_books",
  "profileImage",
  "saves",
  "screenshots",
]

FULL_WIPE_FILES = [
  "command_history.txt",
  "options.txt",
  "patchouli_data.json",
  "usercache.json",
  "usernamecache.json",
]

MINIMAL_WIPE_FOLDERS = [
  "config",
  "defaultconfigs",
  "kubejs",
]

MINIMAL_WIPE_FILES = [
  "options.txt",
]


class HelpFormatter(argparse.HelpFormatter):
  def __init__(self, prog: str) -> None:
    super().__init__(prog, max_help_position=34, width=88)


def refuse_filesystem_root(path: Path) -> None:
  resolved = path.resolve(strict=False)

  if resolved.parent == resolved:
    fail(f"Refusing to use filesystem root as CURSEFORGE_INSTANCE_DIR: {resolved}")


def iter_pack_config_sources(pack_configs_dir: Path) -> list[Path]:
  if not pack_configs_dir.is_dir():
    fail(f"pack-configs folder not found: {pack_configs_dir}")

  return sorted(pack_configs_dir.iterdir())


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Reset a modpack instance and sync project files into it.",
    formatter_class=HelpFormatter,
  )

  parser.add_argument(
    "target_directory_arg",
    nargs="?",
    metavar="INSTANCE_DIR",
    help="Modpack instance directory. If omitted, CURSEFORGE_INSTANCE_DIR from .env is used.",
  )

  parser.add_argument(
    "-t",
    "--target",
    dest="target_directory",
    metavar="INSTANCE_DIR",
    help="Modpack instance directory. If omitted, CURSEFORGE_INSTANCE_DIR from .env is used.",
  )

  parser.add_argument(
    "-f",
    "--full-wipe",
    action="store_true",
    help="Delete additional generated Minecraft instance folders and files.",
  )

  parser.add_argument(
    "-i",
    "--inline",
    action="store_true",
    help="Copy KubeJS and FTB Quests files into the instance without wiping folders.",
  )

  args = parser.parse_args()

  if args.target_directory and args.target_directory_arg:
    fail("Unexpected trailing arguments.")

  target_directory = args.target_directory or args.target_directory_arg

  script_dir = Path(__file__).resolve().parent
  repo_root = script_dir.parent

  pack_configs_dir = repo_root / "pack-configs"

  if is_blank(target_directory):
    instance_dir = get_curseforge_instance_dir()
    print(f"Using {instance_dir} from CURSEFORGE_INSTANCE_DIR")
  else:
    print(f"Using {target_directory} from passed argument")
    try:
      instance_dir = Path(target_directory).expanduser().resolve(strict=False)
    except RuntimeError:
      fail(f"Could not expand home directory in target directory: {target_directory}")

    if not instance_dir.is_dir():
      fail(f"Target Directory does not exist: {instance_dir}")

  if args.inline and args.full_wipe:
    fail("-i/--inline cannot be combined with -f/--full-wipe.")

  refuse_filesystem_root(instance_dir)

  print("======================================")
  print("Reset Modpack and Sync Project")
  print("======================================")
  print(f"Target: {instance_dir}")
  print(f"Full Wipe?: {args.full_wipe}")
  print(f"Inline Update?: {args.inline}")
  print()

  if args.inline:
    inline_copies = [
      ("kubejs", pack_configs_dir / "kubejs", instance_dir / "kubejs"),
      (
        "ftbquests",
        pack_configs_dir / "config" / "ftbquests",
        instance_dir / "config" / "ftbquests",
      ),
    ]

    print("Performing inline sync...")
    for name, source, destination in inline_copies:
      if not source.is_dir():
        fail(f"Source folder not found: {source}")

      print(f"Copying folder {name} ...")
      # Merge into destination without removing existing files (unlike lib_copy_path).
      destination.mkdir(parents=True, exist_ok=True)
      for child in source.rglob("*"):
          rel = child.relative_to(source)
          dest_child = destination / rel
          if child.is_dir():
              dest_child.mkdir(parents=True, exist_ok=True)
          else:
              dest_child.parent.mkdir(parents=True, exist_ok=True)
              shutil.copy2(child, dest_child)

    print()
    print("Inline sync complete!")
    return 0

  if args.full_wipe:
    print("Performing full wipe...")
    folders = FULL_WIPE_FOLDERS
    files = FULL_WIPE_FILES
  else:
    print("Performing MINIMAL wipe...")
    folders = MINIMAL_WIPE_FOLDERS
    files = MINIMAL_WIPE_FILES

  for folder in folders:
    print(f"Deleting folder {folder} ...")
    remove_path(instance_dir / folder)

  for file in files:
    print(f"Deleting file {file} ...")
    remove_path(instance_dir / file)

  shaderpacks_path = instance_dir / "shaderpacks"

  if args.full_wipe and shaderpacks_path.is_dir():
    print("Deleting shaderpacks/*.txt files ...")
    for txt_file in shaderpacks_path.glob("*.txt"):
      remove_path(txt_file)

  print()
  print("Copying pack-configs to instance folder...")

  for source in iter_pack_config_sources(pack_configs_dir):
    destination = instance_dir / source.name
    print(f"Syncing {source.name} ...")
    lib_copy_path(source, destination)

  print()
  print("Modpack reset and synced!")

  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except (OSError, ValueError) as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
