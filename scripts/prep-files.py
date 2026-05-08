#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from lib.env import CURSEFORGE_INSTANCE_DIR, get_curseforge_instance_dir


CLIENT_ONLY_PATTERNS = [
  "appleskin-neoforge-mc1.21-*.jar",
  "arsnumerichud-*.jar",
  "BetterAdvancements-NeoForge-*.jar",
  "betterf3-*.jar",
  "clean_tooltips-*.jar",
  "cleanview-*.jar",
  "configured-*.jar",
  "Controlling-neoforge-*.jar",
  "craftingtweaks-*.jar",
  "craftpresence-*.jar",
  "comforts-*.jar",
  "embeddium-*.jar",
  "enchdesc-neoforge-*.jar",
  "ExtremeSoundMuffler-*.jar",
  "fastipping-*.jar",
  "ftb-chunks-modded-*.jar",
  "inventoryessentials-*.jar",
  "inventorysorter-*.jar",
  "iris-neoforge-*.jar",
  "Jade-*.jar",
  "JadeAddons-*.jar",
  "jearchaeology-*.jar",
  "jeed-*.jar",
  "jei-1.21.1-neoforge-*.jar",
  "justenoughbreeding-neoforge-*.jar",
  "JustEnoughProfessions-neoforge-*.jar",
  "JustEnoughResources-NeoForge-*.jar",
  "moreoverlays-*.jar",
  "MouseTweaks-*.jar",
  "Searchables-neoforge-1.21.1-*.jar",
  "simplemenu-1.21.1-*.jar",
  "sodium-neoforge-*.jar",
  "tipsmod-neoforge-1.21.1-*.jar",
  "timm-*.jar",
  "TravelersTitles-1.21.1-NeoForge-*.jar",
  "villagernames-1.21.1-*.jar",
  "VoidFog-1.21.1-*.jar",
  "yeetusexperimentus-neoforge-*.jar",
]

SERVER_ONLY_PATTERNS = [
  "FarmersStructures-*.jar",
  "HopoBetterRuinedPortals-*.jar",
  "HopoBetterUnderwaterRuins-*.jar",
  "MoogsEndStructures-*.jar",
  "MoogsMissingVillages-*.jar",
  "MoogsNetherStructures-*.jar",
  "MoogsSoaringStructures-*.jar",
  "MoogsTemplesReimagined-*.jar",
  "MoogsVoyagerStructures-*.jar",
  "moogs_structures-*.jar",
  "tidal-towns-*.jar",
]


class HelpFormatter(argparse.HelpFormatter):
  def __init__(self, prog: str) -> None:
    super().__init__(prog, max_help_position=34, width=88)


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


def copy_optional_path(source: Path, destination: Path) -> None:
  if source.exists():
    copy_required_path(source, destination)


def remove_matching_mods(mods_dir: Path, patterns: list[str], label: str) -> None:
  if not mods_dir.is_dir():
    fail(f"Mods folder not found: {mods_dir}")

  for pattern in patterns:
    for mod_file in mods_dir.glob(pattern):
      if mod_file.is_file() or mod_file.is_symlink():
        print(f"Removing {label} mod {mod_file.name} ...")
        mod_file.unlink()


def read_instance_versions(minecraft_instance_json: Path) -> tuple[str | None, str]:
  try:
    instance = json.loads(minecraft_instance_json.read_text(encoding="utf-8"))
  except json.JSONDecodeError as error:
    fail(f"Invalid minecraftinstance.json: {error}")

  minecraft_version = instance.get("gameVersion")

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
  with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(source_dir.rglob("*")):
      archive.write(path, path.relative_to(source_dir))


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Prepare client or server modpack zip files.",
    formatter_class=HelpFormatter,
  )

  target_group = parser.add_mutually_exclusive_group(required=True)
  target_group.add_argument(
    "-c",
    "--client",
    action="store_true",
    help="Prepare client files.",
  )
  target_group.add_argument(
    "-s",
    "--server",
    action="store_true",
    help="Prepare server files.",
  )

  parser.add_argument(
    "-v",
    "--version",
    required=True,
    metavar="VERSION",
    help="Version to include in the output file name, such as 0.1.1.",
  )

  parser.add_argument(
    "-r",
    "--release",
    required=True,
    choices=["alpha", "beta", "release"],
    help="Release channel to include in the output file name.",
  )

  parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    help="Overwrite an existing output zip with the same name.",
  )

  return parser.parse_args()


def validate_version(version: str) -> str:
  if is_blank(version):
    fail("VERSION cannot be empty.")

  if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]*", version):
    fail("VERSION can only contain letters, numbers, dots, underscores, and hyphens.")

  return version


def output_zip_path(
  *,
  repo_root: Path,
  package_type: str,
  version: str,
  release: str,
) -> Path:
  return repo_root / "tmp" / f"varda-{package_type}-{version}-{release}.zip"


def prepare_output_path(zip_file: Path, force: bool) -> None:
  zip_file.parent.mkdir(parents=True, exist_ok=True)

  if not zip_file.exists():
    return

  if not force:
    fail(f"Output already exists: {zip_file}. Pass -f/--force to overwrite it.")


def copy_common_pack_files(
  *,
  instance_dir: Path,
  pack_configs_dir: Path,
  package_dir: Path,
) -> None:
  copy_required_path(pack_configs_dir / "config", package_dir / "config")
  copy_optional_path(pack_configs_dir / "defaultconfigs", package_dir / "defaultconfigs")
  copy_required_path(pack_configs_dir / "kubejs", package_dir / "kubejs")
  copy_required_path(instance_dir / "mods", package_dir / "mods")


def prepare_client_files(
  *,
  instance_dir: Path,
  pack_configs_dir: Path,
  package_dir: Path,
) -> None:
  copy_common_pack_files(
    instance_dir=instance_dir,
    pack_configs_dir=pack_configs_dir,
    package_dir=package_dir,
  )
  copy_required_path(instance_dir / "shaderpacks", package_dir / "shaderpacks")
  remove_matching_mods(package_dir / "mods", SERVER_ONLY_PATTERNS, "server-only")


def prepare_server_files(
  *,
  instance_dir: Path,
  pack_configs_dir: Path,
  package_dir: Path,
) -> None:
  minecraft_instance_json = instance_dir / "minecraftinstance.json"

  if not minecraft_instance_json.is_file():
    fail(f"minecraftinstance.json not found: {minecraft_instance_json}")

  copy_common_pack_files(
    instance_dir=instance_dir,
    pack_configs_dir=pack_configs_dir,
    package_dir=package_dir,
  )
  copy_required_path(minecraft_instance_json, package_dir / "minecraftinstance.json")
  remove_matching_mods(package_dir / "mods", CLIENT_ONLY_PATTERNS, "client-only")

  minecraft_version, neoforge_version = read_instance_versions(minecraft_instance_json)

  print(f"Minecraft version: {minecraft_version}")
  print(f"NeoForge version: {neoforge_version}")

  installer_name = f"neoforge-{neoforge_version}-installer.jar"
  installer_path = package_dir / installer_name
  installer_url = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
    f"{neoforge_version}/{installer_name}"
  )

  download_file(installer_url, installer_path)


def main() -> int:
  args = parse_args()
  package_type = "client" if args.client else "server"
  version = validate_version(args.version)

  script_dir = Path(__file__).resolve().parent
  repo_root = script_dir.parent
  pack_configs_dir = repo_root / "pack-configs"
  zip_file = output_zip_path(
    repo_root=repo_root,
    package_type=package_type,
    version=version,
    release=args.release,
  )

  try:
    instance_dir = get_curseforge_instance_dir()
  except (OSError, ValueError) as error:
    fail(str(error))

  minecraft_instance_json = instance_dir / "minecraftinstance.json"
  if not minecraft_instance_json.is_file():
    fail(f"minecraftinstance.json not found: {minecraft_instance_json}")

  prepare_output_path(zip_file, args.force)

  print(f"Using {instance_dir} from {CURSEFORGE_INSTANCE_DIR}")
  print(f"Preparing {package_type} files")
  print(f"Output: {zip_file}")

  with tempfile.TemporaryDirectory(
    prefix=f"varda-{package_type}-",
    dir=zip_file.parent,
  ) as temp_dir_raw:
    package_dir = Path(temp_dir_raw)

    if args.client:
      prepare_client_files(
        instance_dir=instance_dir,
        pack_configs_dir=pack_configs_dir,
        package_dir=package_dir,
      )
    else:
      prepare_server_files(
        instance_dir=instance_dir,
        pack_configs_dir=pack_configs_dir,
        package_dir=package_dir,
      )

    zip_directory_contents(package_dir, zip_file)

  print(f"Created {zip_file}")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
