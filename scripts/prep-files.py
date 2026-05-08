#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


CLIENT_ONLY_PATTERNS = [
  "appleskin-neoforge-mc1.21-*.jar",
  "betterf3-*.jar",
  "clean_tooltips-*.jar",
  "cleanview-*.jar",
  "configured-*.jar",
  "controlling-*.jar",
  "craftingtweaks-*.jar",
  "craftpresence-*.jar",
  "comforts-*.jar",
  "embeddium-*.jar",
  "enchdesc-neoforge-*.jar",
  "ExtremeSoundMuffler-*.jar",
  "fastipping-*.jar",
  "inventoryessentials-*.jar",
  "inventorysorter-*.jar",
  "Jade-*.jar",
  "JadeAddons-*.jar",
  "jearchaeology-*.jar",
  "jeed-*.jar",
  "jei-1.21.1-neoforge-*.jar",
  "justenoughbreeding-neoforge-*.jar",
  "JustEnoughProfessions-neoforge-*.jar",
  "JustEnoughResources-NeoForge-*.jar",
  "mousetweaks-*.jar",
  "Searchables-neoforge-1.21.1-*.jar",
  "simplemenu-1.21.1-*.jar",
  "tipsmod-neoforge-1.21.1-*.jar",
  "TravelersTitles-1.21.1-NeoForge-*.jar",
  "villagernames-1.21.1-*.jar",
  "VoidFog-1.21.1-*.jar",
  "yeetusexperimentus-neoforge-*.jar",
]


def fail(message: str) -> None:
  print(message, file=sys.stderr)
  raise SystemExit(1)


def is_blank(value: str | None) -> bool:
  return value is None or value.strip() == ""


def copy_required_path(source: Path, destination: Path) -> None:
  if not source.exists():
    fail(f"Source not found: {source}")

  if destination.exists() or destination.is_symlink():
    if destination.is_dir() and not destination.is_symlink():
      shutil.rmtree(destination)
    else:
      destination.unlink()

  if source.is_dir():
    shutil.copytree(source, destination)
  else:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def remove_client_only_mods(server_mods_dir: Path) -> None:
  if not server_mods_dir.is_dir():
    fail(f"Server mods folder not found: {server_mods_dir}")

  for pattern in CLIENT_ONLY_PATTERNS:
    for mod_file in server_mods_dir.glob(pattern):
      if mod_file.is_file() or mod_file.is_symlink():
        print(f"Removing client-only mod {mod_file.name} ...")
        mod_file.unlink()


def read_instance_versions(minecraft_instance_json: Path) -> tuple[str | None, str]:
  try:
    instance = json.loads(minecraft_instance_json.read_text(encoding="utf-8"))
  except json.JSONDecodeError as error:
    fail(f"Invalid minecraftinstance.json: {error}")

  minecraft_version = instance.get("minecraftVersion")

  base_mod_loader = instance.get("baseModLoader")
  if not isinstance(base_mod_loader, dict):
    fail("Could not find baseModLoader in minecraftinstance.json.")

  neoforge_version = base_mod_loader.get("forgeVersion")

  if is_blank(neoforge_version):
    fail("Could not find baseModLoader.forgeVersion in minecraftinstance.json.")

  return minecraft_version, str(neoforge_version)


def download_file(url: str, destination: Path) -> None:
  print(f"Downloading {url}")
  destination.parent.mkdir(parents=True, exist_ok=True)

  try:
    with urllib.request.urlopen(url) as response:
      with destination.open("wb") as output:
        shutil.copyfileobj(response, output)
  except Exception as error:
    fail(f"Download failed: {error}")


def zip_directory_contents(source_dir: Path, zip_file: Path) -> None:
  if zip_file.exists():
    zip_file.unlink()

  with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in source_dir.rglob("*"):
      archive.write(path, path.relative_to(source_dir))


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Prepare a server package from the modpack instance."
  )

  parser.add_argument(
    "pack_dir_arg",
    nargs="?",
    help="Modpack instance folder. If omitted, PACK_DIR.txt is used.",
  )

  parser.add_argument(
    "-t",
    "--pack-dir",
    "-PackDir",
    dest="pack_dir",
    help="Modpack instance folder. If omitted, PACK_DIR.txt is used.",
  )

  args = parser.parse_args()

  if args.pack_dir and args.pack_dir_arg:
    fail("Unexpected trailing arguments.")

  pack_dir_raw = args.pack_dir or args.pack_dir_arg

  script_dir = Path(__file__).resolve().parent
  repo_root = script_dir.parent

  pack_dir_file = repo_root / "PACK_DIR.txt"
  pack_configs_dir = repo_root / "pack-configs"

  if is_blank(pack_dir_raw):
    if not pack_dir_file.is_file():
      fail("PACK_DIR.txt not found. Run scripts/set-pack-dir.py first or pass -t.")

    pack_dir_raw = pack_dir_file.read_text(encoding="utf-8").strip()

  if is_blank(pack_dir_raw):
    fail("PACK_DIR cannot be empty.")

  pack_dir = Path(pack_dir_raw).expanduser().resolve(strict=False)

  minecraft_instance_json = pack_dir / "minecraftinstance.json"
  server_dir = repo_root / "varda-server"
  zip_file = repo_root / "varda-server.zip"

  if not minecraft_instance_json.is_file():
    fail(f"minecraftinstance.json not found: {minecraft_instance_json}")

  print(f"Using PACK_DIR: {pack_dir}")

  if server_dir.exists():
    shutil.rmtree(server_dir)

  server_dir.mkdir(parents=True, exist_ok=True)

  copy_required_path(pack_dir / "mods", server_dir / "mods")
  copy_required_path(minecraft_instance_json, server_dir / "minecraftinstance.json")
  copy_required_path(pack_configs_dir / "config", server_dir / "config")
  copy_required_path(pack_configs_dir / "defaultconfigs", server_dir / "defaultconfigs")
  copy_required_path(pack_configs_dir / "kubejs", server_dir / "kubejs")

  remove_client_only_mods(server_dir / "mods")

  minecraft_version, neoforge_version = read_instance_versions(minecraft_instance_json)

  print(f"Minecraft version: {minecraft_version}")
  print(f"NeoForge version: {neoforge_version}")

  installer_name = f"neoforge-{neoforge_version}-installer.jar"
  installer_path = server_dir / installer_name
  installer_url = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
    f"{neoforge_version}/{installer_name}"
  )

  download_file(installer_url, installer_path)
  zip_directory_contents(server_dir, zip_file)

  print(f"Created {zip_file}")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
