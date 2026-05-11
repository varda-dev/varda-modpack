#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lib.common import fail, log, verbose_log, is_blank, read_json, write_json, copy_path
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
IGNORED_PLACEHOLDER_FILES = {".gitignore"}
TMP_DIR = Path(__file__).resolve().parents[1] / "tmp"
RELEASE_DIR = TMP_DIR / "release"


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


def current_server_mod_download_urls(
  minecraft_instance_json: Path,
  exclude_patterns: list[str],
) -> list[str]:
  instance = read_json(minecraft_instance_json)
  if not isinstance(instance, dict):
    fail("minecraftinstance.json must contain a JSON object.")

  installed_addons = instance.get("installedAddons")
  if not isinstance(installed_addons, list):
    fail("minecraftinstance.json is missing installedAddons.")

  entries: list[tuple[str, int, int, str]] = []
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
    entries.append((str(file_name).lower(), project_id, file_id, url))

  if missing:
    fail(
      "Could not generate complete mods-list.txt; missing download metadata for:\n"
      + "\n".join(f"- {entry}" for entry in missing)
    )

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


def neoforge_installer_url(neoforge_version: str) -> str:
  installer_name = f"neoforge-{neoforge_version}-installer.jar"
  return (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
    f"{neoforge_version}/{installer_name}"
  )


def write_lines(path: Path, lines: list[str]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_mods_list(
  *,
  minecraft_instance_json: Path,
  package_dir: Path,
  exclude_patterns: list[str],
) -> None:
  urls = current_server_mod_download_urls(
    minecraft_instance_json,
    exclude_patterns,
  )
  if not urls:
    fail("No server mod download URLs were generated.")
  write_lines(package_dir / "mods-list.txt", urls)


def write_neoforge_files(
  *,
  package_dir: Path,
  neoforge_version: str,
) -> None:
  write_lines(package_dir / "neoforge-url.txt", [neoforge_installer_url(neoforge_version)])


def clean_directory_contents(directory: Path, *, keep_names: set[str] | None = None) -> None:
  if not directory.exists():
    directory.mkdir(parents=True, exist_ok=True)
    return

  keep = keep_names or set()
  for entry in directory.iterdir():
    if entry.name in keep:
      continue
    if entry.is_dir():
      shutil.rmtree(entry)
    else:
      entry.unlink()


def sync_directory_contents(source: Path, destination: Path) -> None:
  clean_directory_contents(destination, keep_names={"README-SERVER.txt"})
  for entry in sorted(source.iterdir(), key=lambda path: path.name):
    copy_path(entry, destination / entry.name)


def require_go() -> None:
  try:
    subprocess.run(
      ["go", "version"],
      check=True,
      capture_output=True,
      text=True,
    )
  except FileNotFoundError:
    fail("go was not found on PATH.")
  except subprocess.CalledProcessError as error:
    fail(f"go version failed: {error.stderr or error.stdout or error}")


def server_installer_output_path(
  *,
  version: str,
  release: str,
  goos: str,
  goarch: str,
  suffix: str,
) -> Path:
  return RELEASE_DIR / f"varda-server-installer-{version}-{release}-{goos}-{goarch}{suffix}"


def server_installer_targets() -> list[tuple[str, str, str]]:
  return [
    ("windows", "amd64", ".exe"),
    ("linux", "amd64", ""),
    ("linux", "arm64", ""),
    ("darwin", "amd64", ""),
    ("darwin", "arm64", ""),
  ]


def build_server_installers(
  *,
  repo_root: Path,
  version: str,
  release: str,
  force: bool,
  verbose: bool,
) -> list[Path]:
  require_go()

  installer_version = f"{version}-{release}"
  outputs: list[Path] = []
  for goos, goarch, suffix in server_installer_targets():
    output = server_installer_output_path(
      version=version,
      release=release,
      goos=goos,
      goarch=goarch,
      suffix=suffix,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
      if not force:
        fail(f"Output already exists: {output}. Pass -f/--force to overwrite it.")
      output.unlink()

    env = dict(os.environ)
    env["CGO_ENABLED"] = "0"
    env["GOOS"] = goos
    env["GOARCH"] = goarch

    ldflags = (
      f"-s -w -X github.com/rannday/varda-modpack/internal/serverinstaller.Version="
      f"{installer_version}"
    )
    cmd = [
      "go",
      "build",
      "-trimpath",
      "-buildvcs=false",
      "-ldflags",
      ldflags,
      "-o",
      str(output),
      "./cmd/varda-server-installer",
    ]
    verbose_log(
      f"Building {output.name} for {goos}/{goarch}...",
      verbose=verbose,
    )
    try:
      result = subprocess.run(
        cmd,
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
      )
    except FileNotFoundError:
      fail("go was not found on PATH.")
    except subprocess.CalledProcessError as error:
      details = error.stderr or error.stdout or str(error)
      fail(f"go build failed for {goos}/{goarch}: {details}")

    if result.stdout and verbose:
      print(result.stdout, end="")
    if result.stderr and verbose:
      print(result.stderr, end="")

    outputs.append(output)

  return outputs


def zip_directory_contents(source_dir: Path, zip_file: Path) -> None:
  with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(source_dir.rglob("*")):
      archive.write(path, path.relative_to(source_dir))


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Prepare client zip and server installer binaries.",
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
    help="Overwrite existing output files with the same name.",
  )

  parser.add_argument(
    "-q",
    "--quiet",
    action="store_true",
    help="Only print errors and final output file path(s).",
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
  package_type: str,
  version: str,
  release: str,
) -> Path:
  return RELEASE_DIR / f"varda-{package_type}-{version}-{release}.zip"


def prepare_output_paths(zip_files: list[Path], force: bool) -> None:
  for zip_file in zip_files:
    zip_file.parent.mkdir(parents=True, exist_ok=True)
    if zip_file.exists() and not force:
      fail(f"Output already exists: {zip_file}. Pass -f/--force to overwrite it.")


def copy_common_pack_files(
  *,
  pack_configs_dir: Path,
  package_dir: Path,
) -> None:
  copy_path(pack_configs_dir / "config", package_dir / "config")
  if (pack_configs_dir / "defaultconfigs").exists():
    copy_path(pack_configs_dir / "defaultconfigs", package_dir / "defaultconfigs")
  copy_path(pack_configs_dir / "kubejs", package_dir / "kubejs")


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
  instance_dir: Path,
  pack_configs_dir: Path,
  payload_dir: Path,
  quiet: bool,
  verbose: bool,
) -> None:
  minecraft_instance_json = instance_dir / "minecraftinstance.json"

  if not minecraft_instance_json.is_file():
    fail(f"minecraftinstance.json not found: {minecraft_instance_json}")

  copy_common_pack_files(
    pack_configs_dir=pack_configs_dir,
    package_dir=payload_dir,
  )

  minecraft_version, neoforge_version = read_instance_versions(minecraft_instance_json)

  log(f"Minecraft version: {minecraft_version}", quiet=quiet)
  log(f"NeoForge version: {neoforge_version}", quiet=quiet)

  write_mods_list(
    minecraft_instance_json=minecraft_instance_json,
    package_dir=payload_dir,
    exclude_patterns=CLIENT_ONLY_PATTERNS,
  )
  write_neoforge_files(package_dir=payload_dir, neoforge_version=neoforge_version)

  log(f"Prepared server payload in {payload_dir}", quiet=quiet)
  verbose_log(f"Server payload source: {payload_dir}", verbose=verbose, quiet=quiet)


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
  client_zip = output_zip_path(
    package_type="client",
    version=version,
    release=args.release,
  )
  server_outputs = [
    server_installer_output_path(
      version=version,
      release=args.release,
      goos=goos,
      goarch=goarch,
      suffix=suffix,
    )
    for goos, goarch, suffix in server_installer_targets()
  ]

  if "client" in package_types:
    prepare_output_paths([client_zip], args.force)
  if "server" in package_types:
    prepare_output_paths(server_outputs, args.force)

  try:
    instance_dir = get_curseforge_instance_dir()
  except (OSError, ValueError) as error:
    fail(str(error))

  log(f"Using {instance_dir} from {CURSEFORGE_INSTANCE_DIR}", quiet=args.quiet)

  if "client" in package_types:
    log("Preparing client files...", quiet=args.quiet)
    with tempfile.TemporaryDirectory(
      prefix="varda-client-",
      dir=TMP_DIR,
    ) as temp_dir_raw:
      package_dir = Path(temp_dir_raw)
      prepare_client_files(
        instance_dir=instance_dir,
        pack_configs_dir=pack_configs_dir,
        package_dir=package_dir,
      )
      zip_directory_contents(package_dir, client_zip)

    if args.quiet:
      print(client_zip, flush=True)
    else:
      log(f"Created {client_zip}", quiet=args.quiet)

  if "server" in package_types:
    log("Preparing server payload...", quiet=args.quiet)
    payload_dir = repo_root / "cmd" / "varda-server-installer" / "payload"
    with tempfile.TemporaryDirectory(
      prefix="varda-server-payload-",
      dir=TMP_DIR,
    ) as temp_dir_raw:
      temp_payload_dir = Path(temp_dir_raw)
      prepare_server_files(
        instance_dir=instance_dir,
        pack_configs_dir=pack_configs_dir,
        payload_dir=temp_payload_dir,
        quiet=args.quiet,
        verbose=args.verbose,
      )
      sync_directory_contents(temp_payload_dir, payload_dir)

    outputs = build_server_installers(
      repo_root=repo_root,
      version=version,
      release=args.release,
      force=args.force,
      verbose=args.verbose,
    )

    for output in outputs:
      if args.quiet:
        print(output, flush=True)
      else:
        log(f"Created {output}", quiet=args.quiet)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
