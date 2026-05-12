#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import tempfile
import zipfile
from pathlib import Path

from lib.common import copy_path, fail, is_blank, log, read_json, slugify_version, write_json
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
SERVER_CONFIG_EXCLUDE_PATTERNS = [
  "kubejs/client_scripts/**",
  "kubejs/config/defaultoptions.txt",
  "config/simplemenu/**",
  "config/iris.properties",
  "config/simplemenu.json5",
]
IGNORED_PLACEHOLDER_FILES = {".gitignore"}

TMP_DIR = Path(__file__).resolve().parents[1] / "tmp"
RELEASE_DIR = TMP_DIR / "release"
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
MANIFEST_PATH = DOCS_DIR / "manifest.json"
PACK_SLUG = "varda"
DEFAULT_RELEASE = "beta"
GITHUB_REPOSITORY = "varda-dev/varda-modpack"


class HelpFormatter(argparse.HelpFormatter):
  def __init__(self, prog: str) -> None:
    super().__init__(prog, max_help_position=34, width=88)


def matches_any_pattern(file_name: str, patterns: list[str]) -> bool:
  return any(fnmatch.fnmatchcase(file_name, pattern) for pattern in patterns)


def is_server_config_excluded(relative_path: Path) -> bool:
  value = relative_path.as_posix()
  return any(
    fnmatch.fnmatchcase(value, pattern)
    for pattern in SERVER_CONFIG_EXCLUDE_PATTERNS
  )


def copy_optional_populated_path(source: Path, destination: Path) -> None:
  if source.is_dir() and any(
    path.is_file() and path.name not in IGNORED_PLACEHOLDER_FILES
    for path in source.rglob("*")
  ):
    copy_path(source, destination)


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


def addon_display_name(addon: dict[str, object], installed_file: dict[str, object] | None) -> str:
  for value in (
    addon.get("name"),
    addon.get("fileNameOnDisk"),
    installed_file.get("fileName") if installed_file else None,
    installed_file.get("fileNameOnDisk") if installed_file else None,
  ):
    if isinstance(value, str) and value.strip():
      return value

  return "<unnamed addon>"


def addon_file_name(addon: dict[str, object], installed_file: dict[str, object]) -> str | None:
  for value in (
    addon.get("fileNameOnDisk"),
    installed_file.get("fileNameOnDisk"),
    installed_file.get("fileName"),
  ):
    if isinstance(value, str) and value.strip():
      return value

  return None


def metadata_download_url(metadata: object) -> str | None:
  if isinstance(metadata, dict):
    for key in ("downloadUrl", "downloadURL", "download_url", "url"):
      value = metadata.get(key)
      if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value

    for value in metadata.values():
      nested_url = metadata_download_url(value)
      if nested_url is not None:
        return nested_url

  if isinstance(metadata, list):
    for value in metadata:
      nested_url = metadata_download_url(value)
      if nested_url is not None:
        return nested_url

  return None


def current_server_mod_entries(
  minecraft_instance_json: Path,
  exclude_patterns: list[str],
) -> list[dict[str, str]]:
  instance = read_json(minecraft_instance_json)
  if not isinstance(instance, dict):
    fail("minecraftinstance.json must contain a JSON object.")

  installed_addons = instance.get("installedAddons")
  if not isinstance(installed_addons, list):
    fail("minecraftinstance.json is missing installedAddons.")

  entries: list[tuple[str, int, int, dict[str, str]]] = []
  missing: list[str] = []
  seen_keys: set[tuple[int, int]] = set()
  seen_urls: set[str] = set()

  for addon in installed_addons:
    if not isinstance(addon, dict):
      continue

    if addon.get("isEnabled") is False:
      continue

    installed_file = addon.get("installedFile")
    if not isinstance(installed_file, dict):
      missing.append(f"{addon_display_name(addon, None)}: missing installedFile")
      continue

    file_name = addon_file_name(addon, installed_file)
    display_name = addon_display_name(addon, installed_file)
    if is_blank(file_name):
      missing.append(f"{display_name}: missing file name")
      continue

    if not str(file_name).lower().endswith(".jar"):
      continue

    if matches_any_pattern(str(file_name), exclude_patterns):
      continue

    project_id = addon.get("addonID") or addon.get("projectId") or installed_file.get("projectId")
    file_id = installed_file.get("id")

    if not isinstance(project_id, int) or not isinstance(file_id, int):
      missing.append(f"{display_name}: missing project/file ID")
      continue

    key = (project_id, file_id)
    if key in seen_keys:
      continue

    url = metadata_download_url(installed_file)
    if url is None:
      url = metadata_download_url(addon.get("latestFile"))

    if url is None:
      missing.append(f"{display_name} ({project_id}/{file_id}): missing download URL")
      continue

    seen_keys.add(key)
    if url in seen_urls:
      continue

    seen_urls.add(url)
    entries.append(
      (
        str(file_name).lower(),
        project_id,
        file_id,
        {
          "filename": str(file_name),
          "url": url,
        },
      )
    )

  if missing:
    fail(
      "Could not generate complete server mod manifest entries; missing download metadata for:\n"
      + "\n".join(f"- {entry}" for entry in missing)
    )

  if not entries:
    fail("No server mod download entries were generated.")

  entries.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
  return [entry[3] for entry in entries]


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


def read_instance_versions(minecraft_instance_json: Path) -> tuple[str, str]:
  instance = read_json(minecraft_instance_json)
  if not isinstance(instance, dict):
    fail("minecraftinstance.json must contain a JSON object.")

  minecraft_version = instance.get("gameVersion")
  if not isinstance(minecraft_version, str) or is_blank(minecraft_version):
    fail("Could not find gameVersion in minecraftinstance.json.")

  base_mod_loader = instance.get("baseModLoader")
  if not isinstance(base_mod_loader, dict):
    fail("Could not find baseModLoader in minecraftinstance.json.")

  neoforge_version = base_mod_loader.get("forgeVersion")
  if not isinstance(neoforge_version, str) or is_blank(neoforge_version):
    fail("Could not find baseModLoader.forgeVersion in minecraftinstance.json.")

  return minecraft_version, neoforge_version


def neoforge_installer_url(neoforge_version: str) -> str:
  installer_name = f"neoforge-{neoforge_version}-installer.jar"
  return (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
    f"{neoforge_version}/{installer_name}"
  )


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as file:
    while True:
      chunk = file.read(1024 * 1024)
      if not chunk:
        break
      digest.update(chunk)
  return digest.hexdigest()


def server_config_release_url(version: str) -> str:
  return (
    "https://github.com/"
    f"{GITHUB_REPOSITORY}/releases/download/v{version}/"
    f"varda-server-config-{version}.zip"
  )


def server_config_zip_path(version: str) -> Path:
  return RELEASE_DIR / f"varda-server-config-{version}.zip"


def client_zip_path(version: str, release: str) -> Path:
  return RELEASE_DIR / f"{PACK_SLUG}-client-{version}-{release}.zip"


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


def collect_server_config_files(pack_configs_dir: Path) -> list[Path]:
  files: list[Path] = []

  for relative_dir in ("config", "kubejs", "defaultconfigs", "datapacks"):
    source = pack_configs_dir / relative_dir
    if source.is_dir():
      for path in source.rglob("*"):
        if not path.is_file():
          continue
        relative_path = path.relative_to(pack_configs_dir)
        if is_server_config_excluded(relative_path):
          continue
        files.append(path)

  server_readme = pack_configs_dir / "README-SERVER.txt"
  if server_readme.is_file():
    files.append(server_readme)

  files.sort(key=lambda path: path.relative_to(pack_configs_dir).as_posix())
  return files


def fixed_zip_info(arcname: str) -> zipfile.ZipInfo:
  info = zipfile.ZipInfo(arcname)
  info.date_time = (1980, 1, 1, 0, 0, 0)
  info.compress_type = zipfile.ZIP_DEFLATED
  info.external_attr = 0o100644 << 16
  return info


def write_server_config_zip(pack_configs_dir: Path, zip_path: Path) -> None:
  files = collect_server_config_files(pack_configs_dir)
  if not files:
    fail("No server config files were found under pack-configs.")

  zip_path.parent.mkdir(parents=True, exist_ok=True)
  with zipfile.ZipFile(zip_path, "w") as archive:
    for path in files:
      arcname = path.relative_to(pack_configs_dir).as_posix()
      archive.writestr(fixed_zip_info(arcname), path.read_bytes())


def build_manifest(
  *,
  version: str,
  minecraft_version: str,
  neoforge_version: str,
  server_config_hash: str,
  mods: list[dict[str, str]],
) -> dict[str, object]:
  return {
    "schema_version": 1,
    "pack": PACK_SLUG,
    "version": version,
    "minecraft": minecraft_version,
    "neoforge": {
      "version": neoforge_version,
      "installer_url": neoforge_installer_url(neoforge_version),
    },
    "server_config": {
      "url": server_config_release_url(version),
      "sha256": server_config_hash,
    },
    "mods": mods,
  }


def write_pages_files(
  *,
  docs_dir: Path,
  manifest: dict[str, object],
) -> None:
  docs_dir.mkdir(parents=True, exist_ok=True)
  write_json(docs_dir / "manifest.json", manifest)
  docs_dir.joinpath(".nojekyll").touch()


def prepare_output_paths(output_paths: list[Path], force: bool) -> None:
  for output_path in output_paths:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not force:
      fail(f"Output already exists: {output_path}. Pass -f/--force to overwrite it.")


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Prepare Varda client zip, server config ZIP, and Pages manifest.",
    formatter_class=HelpFormatter,
  )

  parser.add_argument(
    "-v",
    "--version",
    required=True,
    metavar="VERSION",
    help="Version to include in output file names, such as 0.1.1.",
  )

  parser.add_argument(
    "-r",
    "--release",
    default=DEFAULT_RELEASE,
    choices=["alpha", "beta", "release"],
    help="Release channel for the client zip name. Default: beta.",
  )

  parser.add_argument(
    "-f",
    "--force",
    action="store_true",
    help="Overwrite existing output files with same name.",
  )

  parser.add_argument(
    "-q",
    "--quiet",
    action="store_true",
    help="Only print errors and final output file paths.",
  )

  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Print detailed progress.",
  )

  return parser.parse_args()


def main() -> int:
  args = parse_args()
  if args.quiet and args.verbose:
    fail("--quiet and --verbose cannot be used together.")

  try:
    version = slugify_version(args.version)
  except (OSError, RuntimeError, ValueError) as error:
    fail(str(error))

  script_dir = Path(__file__).resolve().parent
  repo_root = script_dir.parent
  pack_configs_dir = repo_root / "pack-configs"
  client_zip = client_zip_path(version, args.release)
  server_zip = server_config_zip_path(version)
  manifest_path = MANIFEST_PATH

  prepare_output_paths([client_zip, server_zip], args.force)

  try:
    instance_dir = get_curseforge_instance_dir()
  except (OSError, ValueError) as error:
    fail(str(error))

  log(f"Using {instance_dir} from {CURSEFORGE_INSTANCE_DIR}", quiet=args.quiet)

  if not (instance_dir / "minecraftinstance.json").is_file():
    fail(f"minecraftinstance.json not found: {instance_dir / 'minecraftinstance.json'}")

  log("Preparing client files...", quiet=args.quiet)
  with tempfile.TemporaryDirectory(prefix="varda-client-", dir=TMP_DIR) as temp_dir_raw:
    package_dir = Path(temp_dir_raw)
    prepare_client_files(
      instance_dir=instance_dir,
      pack_configs_dir=pack_configs_dir,
      package_dir=package_dir,
    )
    package_dir_zip = client_zip
    with zipfile.ZipFile(package_dir_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
      for path in sorted(package_dir.rglob("*")):
        archive.write(path, path.relative_to(package_dir))

  log(f"Created {client_zip}", quiet=args.quiet)

  minecraft_instance_json = instance_dir / "minecraftinstance.json"
  minecraft_version, neoforge_version = read_instance_versions(minecraft_instance_json)
  log(f"Minecraft version: {minecraft_version}", quiet=args.quiet)
  log(f"NeoForge version: {neoforge_version}", quiet=args.quiet)

  log("Preparing server config ZIP...", quiet=args.quiet)
  write_server_config_zip(pack_configs_dir, server_zip)
  server_config_hash = sha256_file(server_zip)
  log(f"Created {server_zip}", quiet=args.quiet)

  mods = current_server_mod_entries(minecraft_instance_json, CLIENT_ONLY_PATTERNS)
  manifest = build_manifest(
    version=version,
    minecraft_version=minecraft_version,
    neoforge_version=neoforge_version,
    server_config_hash=server_config_hash,
    mods=mods,
  )

  write_pages_files(docs_dir=DOCS_DIR, manifest=manifest)

  if args.quiet:
    print(client_zip, flush=True)
    print(server_zip, flush=True)
    print(manifest_path, flush=True)
  else:
    log(f"Created {manifest_path}", quiet=args.quiet)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
