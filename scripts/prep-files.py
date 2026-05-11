#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from lib.common import fail, log, verbose_log, is_blank, read_json, write_json, remove_path, copy_path
from lib.env import CURSEFORGE_INSTANCE_DIR, get_curseforge_instance_dir


CLIENT_ONLY_PATTERNS = [
  "appleskin-neoforge-mc1.21-*.jar",
  "arsnumerichud-*.jar",
  "Controlling-neoforge-*.jar",
  "enchdesc-neoforge-*.jar",
  "bookshelf-neoforge-*.jar",
  "prickle-neoforge-*.jar",
  "moreoverlays-*.jar",
  "simplemenu-1.21.1-*.jar",
  "collective-*.jar",
  "MouseTweaks-*.jar",
  "inventoryessentials-*.jar",
  "craftingtweaks-*.jar",
  "balm-neoforge-*.jar",
  "jei-1.21.1-neoforge-*.jar",
  "Searchables-neoforge-1.21.1-*.jar",
  "iris-neoforge-*.jar",
  "sodium-neoforge-*.jar",
  "Jade-*.jar",
]

SERVER_ONLY_PATTERNS = []
IGNORED_PLACEHOLDER_FILES = {".gitignore", ".gitkeep"}


class HelpFormatter(argparse.HelpFormatter):
  def __init__(self, prog: str) -> None:
    super().__init__(prog, max_help_position=34, width=88)


def matches_any_pattern(file_name: str, patterns: list[str]) -> bool:
  return any(fnmatch.fnmatchcase(file_name, pattern) for pattern in patterns)


def copy_optional_populated_path(source: Path, destination: Path) -> None:
  if source.is_dir() and any(
    path.is_file() and path.name not in IGNORED_PLACEHOLDER_FILES
    for path in source.rglob("*")
  ):
    copy_path(source, destination)


def run_command(command: list[str], cwd: Path, *, quiet: bool, verbose: bool) -> None:
  try:
    if verbose and not quiet:
      subprocess.run(command, cwd=cwd, check=True)
      return

    result = subprocess.run(
      command,
      cwd=cwd,
      check=False,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
    )
    if result.returncode != 0:
      output = "\n".join(
        part.strip()
        for part in (result.stdout, result.stderr)
        if part and part.strip()
      )
      details = f"\n\nCommand output:\n{output}" if output else ""
      fail(
        f"Command failed with exit code {result.returncode}: {' '.join(command)}"
        f"{details}"
      )
  except FileNotFoundError:
    if command and command[0] == "java":
      fail("Java was not found. Java 21 is required.")
    fail(f"Command not found: {' '.join(command)}")


def current_installed_manifest_files(
  minecraft_instance_json: Path,
  exclude_patterns: list[str],
) -> list[dict[str, object]]:
  instance = read_json(minecraft_instance_json)
  if not isinstance(instance, dict):
    fail("minecraftinstance.json must contain a JSON object.")

  installed_addons = instance.get("installedAddons")
  if not isinstance(installed_addons, list):
    fail("minecraftinstance.json is missing installedAddons.")

  files: list[dict[str, object]] = []
  seen: set[tuple[int, int]] = set()

  for addon in installed_addons:
    if not isinstance(addon, dict):
      continue

    if addon.get("isEnabled") is False:
      continue

    installed_file = addon.get("installedFile")
    if not isinstance(installed_file, dict):
      continue

    file_name = addon.get("fileNameOnDisk") or installed_file.get("fileName")
    if isinstance(file_name, str) and matches_any_pattern(file_name, exclude_patterns):
      continue

    project_id = addon.get("addonID") or addon.get("projectId") or installed_file.get("projectId")
    file_id = installed_file.get("id")

    if not isinstance(project_id, int) or not isinstance(file_id, int):
      continue

    key = (project_id, file_id)
    if key in seen:
      continue

    seen.add(key)
    files.append(
      {
        "projectID": project_id,
        "fileID": file_id,
        "required": True,
      }
    )

  files.sort(key=lambda entry: (entry["projectID"], entry["fileID"]))
  return files


def copy_client_manifest(
  *,
  instance_dir: Path,
  package_dir: Path,
  server_only_patterns: list[str],
) -> None:
  source = instance_dir / "manifest.json"
  minecraft_instance_json = instance_dir / "minecraftinstance.json"

  if not source.is_file():
    fail(f"manifest.json not found: {source}")

  manifest = read_json(source)
  if not isinstance(manifest, dict):
    fail("manifest.json must contain a JSON object.")

  manifest["overrides"] = "overrides"
  manifest["files"] = current_installed_manifest_files(
    minecraft_instance_json,
    server_only_patterns,
  )

  write_json(package_dir / "manifest.json", manifest)


def read_instance_versions(minecraft_instance_json: Path) -> tuple[str | None, str]:
  instance = read_json(minecraft_instance_json)
  if not isinstance(instance, dict):
    fail("minecraftinstance.json must contain a JSON object.")

  minecraft_version = instance.get("gameVersion")

  base_mod_loader = instance.get("baseModLoader")
  if not isinstance(base_mod_loader, dict):
    fail("Could not find baseModLoader in minecraftinstance.json.")

  neoforge_version = base_mod_loader.get("forgeVersion")

  if is_blank(neoforge_version):
    fail("Could not find baseModLoader.forgeVersion in minecraftinstance.json.")

  return minecraft_version, str(neoforge_version)


def download_file(url: str, destination: Path, *, quiet: bool) -> None:
  log(f"Downloading {url}", quiet=quiet)
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
    description="Prepare client, server, or both modpack zip files.",
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
  target_group.add_argument(
    "-b",
    "--both",
    action="store_true",
    help="Prepare both client and server files.",
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

  parser.add_argument(
    "-q",
    "--quiet",
    action="store_true",
    help="Only print errors and final output zip path(s).",
  )

  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Print detailed progress and subprocess output.",
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


def prepare_output_paths(zip_files: list[Path], force: bool) -> None:
  for zip_file in zip_files:
    zip_file.parent.mkdir(parents=True, exist_ok=True)
    if zip_file.exists() and not force:
      fail(f"Output already exists: {zip_file}. Pass -f/--force to overwrite it.")


def copy_common_pack_files(
  *,
  instance_dir: Path,
  pack_configs_dir: Path,
  package_dir: Path,
  ignore_patterns: list[str] | None = None,
) -> None:
  copy_path(pack_configs_dir / "config", package_dir / "config")
  if (pack_configs_dir / "defaultconfigs").exists():
    copy_path(pack_configs_dir / "defaultconfigs", package_dir / "defaultconfigs")
  copy_path(pack_configs_dir / "kubejs", package_dir / "kubejs")
  copy_path(instance_dir / "mods", package_dir / "mods", ignore_patterns=ignore_patterns)


def copy_server_support_files(*, repo_root: Path, package_dir: Path) -> None:
  server_files_dir = repo_root / "server-files"
  copy_path(server_files_dir / "README-SERVER.txt", package_dir / "README-SERVER.txt")
  if (server_files_dir / "server.properties").exists():
    copy_path(
      server_files_dir / "server.properties",
      package_dir / "server.properties",
    )


def patch_server_launchers(package_dir: Path, neoforge_version: str) -> None:
  run_sh = package_dir / "run.sh"
  run_bat = package_dir / "run.bat"
  user_jvm_args = package_dir / "user_jvm_args.txt"

  if not run_sh.is_file():
    fail(f"run.sh not found after NeoForge installation: {run_sh}")
  if not run_bat.is_file():
    fail(f"run.bat not found after NeoForge installation: {run_bat}")
  if not user_jvm_args.is_file():
    fail(f"user_jvm_args.txt not found after NeoForge installation: {user_jvm_args}")

  run_sh_text = run_sh.read_text(encoding="utf-8")
  old_run_sh = (
    f'java @user_jvm_args.txt '
    f'@libraries/net/neoforged/neoforge/{neoforge_version}/unix_args.txt "$@"'
  )
  new_run_sh = (
    f'java @user_jvm_args.txt '
    f'@libraries/net/neoforged/neoforge/{neoforge_version}/unix_args.txt nogui "$@"'
  )
  if old_run_sh not in run_sh_text:
    fail("run.sh did not contain the expected NeoForge launch command.")
  run_sh.write_text(run_sh_text.replace(old_run_sh, new_run_sh, 1), encoding="utf-8")

  run_bat_text = run_bat.read_text(encoding="utf-8")
  old_run_bat = (
    f'java @user_jvm_args.txt '
    f'@libraries/net/neoforged/neoforge/{neoforge_version}/win_args.txt %*'
  )
  new_run_bat = (
    f'java @user_jvm_args.txt '
    f'@libraries/net/neoforged/neoforge/{neoforge_version}/win_args.txt nogui %*'
  )
  if old_run_bat not in run_bat_text:
    fail("run.bat did not contain the expected NeoForge launch command.")
  run_bat.write_text(run_bat_text.replace(old_run_bat, new_run_bat, 1), encoding="utf-8")

  user_jvm_args.write_text(
    "# JVM memory settings for Varda.\n"
    "# Adjust these based on available server RAM.\n"
    "-Xms4G\n"
    "-Xmx6G\n",
    encoding="utf-8",
  )


def cleanup_installer_files(package_dir: Path, installer_name: str) -> None:
  remove_path(package_dir / installer_name)
  remove_path(package_dir / f"{installer_name}.log")


def prepare_client_files(
  *,
  instance_dir: Path,
  pack_configs_dir: Path,
  package_dir: Path,
) -> None:
  overrides_dir = package_dir / "overrides"

  copy_client_manifest(
    instance_dir=instance_dir,
    package_dir=package_dir,
    server_only_patterns=SERVER_ONLY_PATTERNS,
  )
  copy_path(instance_dir / "modlist.html", package_dir / "modlist.html")

  copy_path(pack_configs_dir / "config", overrides_dir / "config")
  copy_path(pack_configs_dir / "kubejs", overrides_dir / "kubejs")
  copy_optional_populated_path(pack_configs_dir / "shaderpacks", overrides_dir / "shaderpacks")
  copy_optional_populated_path(pack_configs_dir / "datapacks", overrides_dir / "datapacks")
  copy_optional_populated_path(pack_configs_dir / "resourcepacks", overrides_dir / "resourcepacks")


def prepare_server_files(
  *,
  repo_root: Path,
  instance_dir: Path,
  pack_configs_dir: Path,
  package_dir: Path,
  quiet: bool,
  verbose: bool,
) -> None:
  minecraft_instance_json = instance_dir / "minecraftinstance.json"

  if not minecraft_instance_json.is_file():
    fail(f"minecraftinstance.json not found: {minecraft_instance_json}")

  copy_common_pack_files(
    instance_dir=instance_dir,
    pack_configs_dir=pack_configs_dir,
    package_dir=package_dir,
    ignore_patterns=CLIENT_ONLY_PATTERNS,
  )
  copy_path(minecraft_instance_json, package_dir / "minecraftinstance.json")
  copy_server_support_files(repo_root=repo_root, package_dir=package_dir)

  minecraft_version, neoforge_version = read_instance_versions(minecraft_instance_json)

  log(f"Minecraft version: {minecraft_version}", quiet=quiet)
  log(f"NeoForge version: {neoforge_version}", quiet=quiet)

  installer_name = f"neoforge-{neoforge_version}-installer.jar"
  installer_path = package_dir / installer_name
  installer_url = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
    f"{neoforge_version}/{installer_name}"
  )

  download_file(installer_url, installer_path, quiet=quiet)
  install_neoforge_server(
    package_dir,
    installer_name,
    quiet=quiet,
    verbose=verbose,
  )
  cleanup_installer_files(package_dir, installer_name)
  patch_server_launchers(package_dir, neoforge_version)


def main() -> int:
  args = parse_args()
  if args.quiet and args.verbose:
    fail("--quiet and --verbose cannot be used together.")
  version = validate_version(args.version)

  if args.client:
    package_types = ["client"]
  elif args.server:
    package_types = ["server"]
  else:
    package_types = ["client", "server"]

  script_dir = Path(__file__).resolve().parent
  repo_root = script_dir.parent
  pack_configs_dir = repo_root / "pack-configs"
  zip_files = {
    package_type: output_zip_path(
      repo_root=repo_root,
      package_type=package_type,
      version=version,
      release=args.release,
    )
    for package_type in package_types
  }

  prepare_output_paths(list(zip_files.values()), args.force)

  try:
    instance_dir = get_curseforge_instance_dir()
  except (OSError, ValueError) as error:
    fail(str(error))

  log(f"Using {instance_dir} from {CURSEFORGE_INSTANCE_DIR}", quiet=args.quiet)

  for package_type in package_types:
    zip_file = zip_files[package_type]
    log(f"Preparing {package_type} files...", quiet=args.quiet)

    with tempfile.TemporaryDirectory(
      prefix=f"varda-{package_type}-",
      dir=zip_file.parent,
    ) as temp_dir_raw:
      package_dir = Path(temp_dir_raw)

      if package_type == "client":
        prepare_client_files(
          instance_dir=instance_dir,
          pack_configs_dir=pack_configs_dir,
          package_dir=package_dir,
        )
      else:
        prepare_server_files(
          repo_root=repo_root,
          instance_dir=instance_dir,
          pack_configs_dir=pack_configs_dir,
          package_dir=package_dir,
          quiet=args.quiet,
          verbose=args.verbose,
        )

      zip_directory_contents(package_dir, zip_file)

    if args.quiet:
      print(zip_file, flush=True)
    else:
      log(f"Created {zip_file}", quiet=args.quiet)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
