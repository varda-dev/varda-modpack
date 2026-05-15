from __future__ import annotations

import argparse
import errno
import fnmatch
import hashlib
import http.client
import json
import mimetypes
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote, urlencode

from lib.common import copy_path, fail, is_blank, log, read_json, remove_path, slugify_version, write_json
from lib.env import (
  CURSEFORGE_INSTANCE_DIR,
  REPO_ROOT,
  get_curseforge_api_token,
  get_curseforge_instance_dir,
  get_github_releases_pat,
)
from lib.http import (
  HttpRequestError,
  http_request,
  request_url_parts,
  response_body_to_text,
  retry_delay_for_attempt as shared_retry_delay_for_attempt,
)
from lib.manifest_schema import validate_manifest_against_schema


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
UPLOAD_DIR = RELEASE_DIR
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
MANIFEST_PATH = DOCS_DIR / "manifest.json"
PACK_SLUG = "varda"
PACK_DISPLAY_NAME = "Varda"
DEFAULT_RELEASE = "beta"
GITHUB_REPOSITORY = "varda-dev/varda-modpack"
SHA1_RE = re.compile(r"\b[0-9a-fA-F]{40}\b")
DEFAULT_BASE_URL = "https://minecraft.curseforge.com"
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024
PROJECT_ID = "533644"
DEFAULT_UPLOAD_MAX_ATTEMPTS = 3
DEFAULT_UPLOAD_RETRY_BASE_DELAY = 5
MAX_CURSEFORGE_UPLOAD_SIZE = 500 * 1000 * 1000
GAME_VERSIONS = [11779, 10150]
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_GITHUB_API_BASE = "https://api.github.com"
DEFAULT_GITHUB_API_MAX_ATTEMPTS = 3
DEFAULT_GITHUB_RETRY_BASE_DELAY = 5
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


class HelpFormatter(argparse.HelpFormatter):
  def __init__(self, prog: str) -> None:
    super().__init__(prog, max_help_position=24, width=72)


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


def optional_http_url(value: object) -> str | None:
  if isinstance(value, str):
    value = value.strip()
    if value.startswith(("http://", "https://")):
      return value

  return None


def metadata_http_url(metadata: object) -> str | None:
  if isinstance(metadata, dict):
    for key in ("downloadUrl", "downloadURL", "download_url", "url"):
      value = optional_http_url(metadata.get(key))
      if value is not None:
        return value

    for value in metadata.values():
      nested_url = metadata_http_url(value)
      if nested_url is not None:
        return nested_url

  if isinstance(metadata, list):
    for value in metadata:
      nested_url = metadata_http_url(value)
      if nested_url is not None:
        return nested_url

  return None


def curseforge_hashes(installed_file: dict[str, object]) -> dict[str, str]:
  hashes = installed_file.get("hashes")
  if not isinstance(hashes, list):
    return {}

  result: dict[str, str] = {}
  for hash_entry in hashes:
    if not isinstance(hash_entry, dict):
      continue

    value = hash_entry.get("value")
    if isinstance(value, str):
      hash_value = value.strip()
    else:
      hash_value = None

    if not hash_value:
      continue

    hash_type = hash_entry.get("type")
    if hash_type == 1:
      result["sha1"] = hash_value

  return result


def read_instance_json(minecraft_instance_json: Path) -> dict[str, object]:
  instance = read_json(minecraft_instance_json)
  if not isinstance(instance, dict):
    fail("minecraftinstance.json must contain a JSON object.")

  return instance


def neoforge_installer_url(neoforge_version: str) -> str:
  installer_name = f"neoforge-{neoforge_version}-installer.jar"
  return (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
    f"{neoforge_version}/{installer_name}"
  )


def neoforge_installer_sha1_url(neoforge_version: str) -> str:
  return f"{neoforge_installer_url(neoforge_version)}.sha1"


def fetch_text(url: str) -> str:
  try:
    with urllib.request.urlopen(url, timeout=30) as response:
      return response.read().decode("utf-8", errors="replace")
  except urllib.error.URLError as error:
    fail(f"Could not fetch {url}: {error}")


def parse_sha1_digest(data: str, label: str) -> str:
  match = SHA1_RE.search(data)
  if match is None:
    fail(f"Could not find SHA-1 digest in {label}.")

  return match.group(0).lower()


def neoforge_metadata(
  neoforge_version: str,
) -> dict[str, object]:
  sha1_url = neoforge_installer_sha1_url(neoforge_version)
  sha1 = parse_sha1_digest(fetch_text(sha1_url), sha1_url)
  neoforge: dict[str, object] = {
    "version": neoforge_version,
    "installer_url": neoforge_installer_url(neoforge_version),
    "sha1": sha1,
  }

  return neoforge


def current_server_mod_entries(
  minecraft_instance_json: Path,
  exclude_patterns: list[str],
) -> list[dict[str, object]]:
  instance = read_instance_json(minecraft_instance_json)
  installed_addons = instance.get("installedAddons")
  if not isinstance(installed_addons, list):
    fail("minecraftinstance.json is missing installedAddons.")

  entries: list[tuple[str, int, int, dict[str, object]]] = []
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

    url = metadata_http_url(installed_file)
    if url is None:
      url = metadata_http_url(addon.get("latestFile"))

    if url is None:
      missing.append(f"{display_name} ({project_id}/{file_id}): missing download URL")
      continue

    hashes = curseforge_hashes(installed_file)
    if "sha1" not in hashes:
      missing.append(f"{display_name} ({project_id}/{file_id}): missing sha1 hash")
      continue

    seen_keys.add(key)
    if url in seen_urls:
      continue

    seen_urls.add(url)
    addon_name = addon.get("name")
    if isinstance(addon_name, str) and addon_name.strip():
      entry_name = addon_name.strip()
    else:
      entry_name = display_name

    entry: dict[str, object] = {
      "name": entry_name,
      "url": url,
    }

    website_url = optional_http_url(addon.get("webSiteURL"))
    if website_url is not None:
      entry["website_url"] = website_url

    sha1 = hashes.get("sha1")
    if sha1:
      entry["sha1"] = sha1

    size = installed_file.get("fileLength")
    if isinstance(size, int):
      entry["size"] = size

    entries.append(
      (
        str(file_name).lower(),
        project_id,
        file_id,
        entry,
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
  version: str,
) -> None:
  source = instance_dir / "manifest.json"
  minecraft_instance_json = instance_dir / "minecraftinstance.json"

  if not source.is_file():
    fail(f"manifest.json not found: {source}")

  manifest = read_json(source)
  if not isinstance(manifest, dict):
    fail("manifest.json must contain a JSON object.")

  minecraft_version, neoforge_version = read_instance_versions(minecraft_instance_json)

  manifest["version"] = version
  manifest["overrides"] = "overrides"
  manifest["files"] = current_installed_manifest_files(
    minecraft_instance_json,
    server_only_patterns,
  )

  minecraft = manifest.get("minecraft")
  if not isinstance(minecraft, dict):
    minecraft = {}

  minecraft["version"] = minecraft_version
  minecraft["modLoaders"] = [
    {
      "id": f"neoforge-{neoforge_version}",
      "primary": True,
    }
  ]

  manifest["minecraft"] = minecraft

  manifest_path = package_dir / "manifest.json"
  write_json(manifest_path, manifest)
  validate_client_manifest(
    manifest_path,
    expected_minecraft_version=minecraft_version,
    expected_neoforge_version=neoforge_version,
    expected_pack_version=version,
  )


def validate_client_manifest(
  manifest_path: Path,
  *,
  expected_minecraft_version: str,
  expected_neoforge_version: str,
  expected_pack_version: str,
) -> None:
  manifest = read_json(manifest_path)

  if not isinstance(manifest, dict):
    fail("Generated client manifest must contain a JSON object.")

  if manifest.get("version") != expected_pack_version:
    fail(
      "Generated client manifest has wrong pack version: "
      f"{manifest.get('version')!r}; expected {expected_pack_version!r}."
    )

  minecraft = manifest.get("minecraft")
  if not isinstance(minecraft, dict):
    fail("Generated client manifest is missing minecraft object.")

  if minecraft.get("version") != expected_minecraft_version:
    fail(
      "Generated client manifest has wrong Minecraft version: "
      f"{minecraft.get('version')!r}; expected {expected_minecraft_version!r}."
    )

  expected_loader_id = f"neoforge-{expected_neoforge_version}"
  mod_loaders = minecraft.get("modLoaders")

  if not isinstance(mod_loaders, list):
    fail("Generated client manifest is missing minecraft.modLoaders list.")

  if not any(
    isinstance(loader, dict)
    and loader.get("id") == expected_loader_id
    and loader.get("primary") is True
    for loader in mod_loaders
  ):
    fail(
      "Generated client manifest is missing expected primary NeoForge loader: "
      f"{expected_loader_id}."
    )


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


def sha1_file(path: Path) -> str:
  digest = hashlib.sha1()
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
  version: str,
) -> None:
  overrides_dir = package_dir / "overrides"

  copy_client_manifest(
    instance_dir=instance_dir,
    package_dir=package_dir,
    server_only_patterns=SERVER_ONLY_PATTERNS,
    version=version,
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
  neoforge: dict[str, object],
  server_config_sha1: str,
  mods: list[dict[str, object]],
) -> dict[str, object]:
  return {
    "version": version,
    "pack": PACK_SLUG,
    "schema_version": 2,
    "minecraft": minecraft_version,
    "neoforge": neoforge,
    "server_config": {
      "url": server_config_release_url(version),
      "sha1": server_config_sha1,
    },
    "mods": mods,
  }


def write_pages_files(
  *,
  docs_dir: Path,
  manifest: dict[str, object],
) -> None:
  docs_dir.mkdir(parents=True, exist_ok=True)
  write_json(docs_dir / "manifest.json", manifest, sort_keys=False)
  docs_dir.joinpath(".nojekyll").touch()


def prepare_output_paths(output_paths: list[Path], force: bool) -> None:
  for output_path in output_paths:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not force:
      fail(f"Output already exists: {output_path}. Pass -f/--force to overwrite it.")


def format_file_size(size: int) -> str:
  return f"{size / 1000 / 1000:.1f} MB"


def validate_upload_file_size(file_path: Path) -> None:
  size = file_path.stat().st_size

  if size > MAX_CURSEFORGE_UPLOAD_SIZE:
    fail(
      "upload file is too large for CurseForge API: "
      f"{file_path} is {format_file_size(size)}; "
      f"limit is {format_file_size(MAX_CURSEFORGE_UPLOAD_SIZE)}. "
      "CurseForge/Cloudflare is likely to reject this with HTTP 413 "
      "Payload Too Large, which may appear as Broken pipe."
    )


def build_client_metadata(
  *,
  version: str,
  release_type: str,
  changelog: str,
) -> dict[str, Any]:
  metadata: dict[str, Any] = {
    "changelog": changelog,
    "changelogType": "text",
    "releaseType": release_type,
    "isMarkedForManualRelease": False,
    "displayName": f"{PACK_DISPLAY_NAME} {version}",
    "gameVersions": GAME_VERSIONS,
  }
  return metadata


def resolve_client_artifact(
  *,
  version: str,
  release_type: str,
) -> Path:
  return client_artifact_path(version, release_type)


def print_metadata(metadata: dict[str, Any]) -> None:
  print("Metadata:")
  print(json.dumps(metadata, indent=2))


def upload_artifact(
  *,
  token: str,
  version: str,
  release_type: str,
  changelog: str,
  dry_run: bool,
) -> dict[str, Any]:
  file_path = resolve_client_artifact(version=version, release_type=release_type)
  metadata = build_client_metadata(
    version=version,
    release_type=release_type,
    changelog=changelog,
  )

  if not file_path.is_file():
    fail(f"upload file not found: {file_path}")

  file_size = file_path.stat().st_size
  validate_upload_file_size(file_path)

  print("CurseForge upload:")
  print(f"  project ID:     {PROJECT_ID}")
  print(f"  file:           {file_path}")
  print(f"  file size:      {format_file_size(file_size)}")
  print(f"  display name:   {metadata['displayName']}")
  print(f"  release type:   {release_type}")
  print(f"  game versions:  {metadata['gameVersions']}")

  print()

  if dry_run:
    print_metadata(metadata)
    return {}

  return upload_file(
    base_url=DEFAULT_BASE_URL,
    token=token,
    project_id=PROJECT_ID,
    file_path=file_path,
    metadata=metadata,
  )


def is_retryable_upload_error(err: BaseException) -> bool:
  current: BaseException | None = err
  seen: set[int] = set()

  while current is not None and id(current) not in seen:
    seen.add(id(current))

    if isinstance(current, (BrokenPipeError, ConnectionResetError, TimeoutError)):
      return True

    if isinstance(current, OSError) and current.errno in {
      errno.EPIPE,
      errno.ECONNRESET,
      errno.ETIMEDOUT,
      errno.EAGAIN,
    }:
      return True

    cause = current.__cause__
    current = cause if isinstance(cause, BaseException) else None

  return False


def is_retryable_http_status(status: int) -> bool:
  return status >= 500 or status == 429


def multipart_field_part(boundary: str, name: str, value: str) -> bytes:
  header = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
  ).encode("utf-8")

  return header + value.encode("utf-8") + b"\r\n"


def multipart_file_header(boundary: str, name: str, path: Path) -> bytes:
  filename = path.name
  content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

  return (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
    f"Content-Type: {content_type}\r\n\r\n"
  ).encode("utf-8")


def multipart_content_length(
  boundary: str,
  fields: dict[str, str],
  files: dict[str, Path],
) -> int:
  length = 0

  for name, value in fields.items():
    length += len(multipart_field_part(boundary, name, value))

  for name, path in files.items():
    length += len(multipart_file_header(boundary, name, path))
    length += path.stat().st_size
    length += len(b"\r\n")

  length += len(f"--{boundary}--\r\n".encode("utf-8"))
  return length


def iter_multipart_chunks(
  boundary: str,
  fields: dict[str, str],
  files: dict[str, Path],
) -> Iterator[bytes]:
  for name, value in fields.items():
    yield multipart_field_part(boundary, name, value)

  for name, path in files.items():
    yield multipart_file_header(boundary, name, path)

    with path.open("rb") as file:
      while True:
        chunk = file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
          break
        yield chunk

    yield b"\r\n"

  yield f"--{boundary}--\r\n".encode("utf-8")


def parse_upload_response(raw: str) -> dict[str, Any]:
  if not raw.strip():
    return {}

  try:
    return json.loads(raw)
  except json.JSONDecodeError:
    fail(f"CurseForge upload returned invalid JSON:\n{raw}")


def upload_file_once(
  *,
  base_url: str,
  token: str,
  project_id: str,
  file_path: Path,
  metadata: dict[str, Any],
) -> dict[str, Any]:
  url = f"{base_url.rstrip('/')}/api/projects/{project_id}/upload-file"
  boundary = f"----curseforge-upload-{uuid.uuid4().hex}"
  fields = {"metadata": json.dumps(metadata)}
  files = {"file": file_path}
  content_type = f"multipart/form-data; boundary={boundary}"
  content_length = multipart_content_length(boundary, fields, files)

  scheme, host, path = request_url_parts(url, label="CurseForge upload URL")
  connection: http.client.HTTPConnection | None = None

  try:
    connection_class = (
      http.client.HTTPSConnection
      if scheme == "https"
      else http.client.HTTPConnection
    )
    connection = connection_class(host, timeout=120)
    connection.putrequest("POST", path)
    connection.putheader("X-Api-Token", token)
    connection.putheader("Content-Type", content_type)
    connection.putheader("Content-Length", str(content_length))
    connection.putheader("Accept", "application/json")
    connection.putheader("User-Agent", "curseforge-modpack-uploader/1.0")
    connection.endheaders()

    for chunk in iter_multipart_chunks(boundary, fields, files):
      connection.send(chunk)

    response = connection.getresponse()
    raw = response.read().decode("utf-8", errors="replace")

    if response.status < 200 or response.status >= 300:
      raise CurseForgeUploadError(
        f"CurseForge upload failed: HTTP {response.status} {response.reason}\n{raw}",
        http_status=response.status,
      )

    return parse_upload_response(raw)

  except (OSError, http.client.HTTPException) as err:
    raise CurseForgeUploadError(f"CurseForge upload failed: {err}") from err

  finally:
    if connection is not None:
      connection.close()


def upload_file(
  *,
  base_url: str,
  token: str,
  project_id: str,
  file_path: Path,
  metadata: dict[str, Any],
  max_attempts: int = DEFAULT_UPLOAD_MAX_ATTEMPTS,
) -> dict[str, Any]:
  last_err: BaseException | None = None

  for attempt in range(1, max_attempts + 1):
    try:
      return upload_file_once(
        base_url=base_url,
        token=token,
        project_id=project_id,
        file_path=file_path,
        metadata=metadata,
      )
    except CurseForgeUploadError as err:
      last_err = err

      retryable = (
        (err.http_status is not None and is_retryable_http_status(err.http_status))
        or is_retryable_upload_error(err)
      )

      if not retryable or attempt >= max_attempts:
        raise

      delay = shared_retry_delay_for_attempt(attempt, base_delay=DEFAULT_UPLOAD_RETRY_BASE_DELAY)
      print(
        f"CurseForge upload failed on attempt {attempt}/{max_attempts}; "
        f"retrying in {delay}s.",
        file=sys.stderr,
      )
      time.sleep(delay)

  assert last_err is not None
  raise last_err


def split_repository(repository: str) -> tuple[str, str]:
  value = repository.strip()
  if not value or "/" not in value:
    fail(f"Invalid GitHub repository value: {repository!r}")

  owner, name = value.split("/", 1)
  owner = owner.strip()
  name = name.strip()
  if not owner or not name:
    fail(f"Invalid GitHub repository value: {repository!r}")

  return owner, name


def repository_path(repository: str) -> str:
  owner, name = split_repository(repository)
  return f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}"


def server_config_asset_path(version: str) -> Path:
  return UPLOAD_DIR / f"varda-server-config-{version}.zip"


def github_api_request(
  method: str,
  url: str,
  token: str,
  *,
  json_body: Any | None = None,
  headers: dict[str, str] | None = None,
  raw_body: bytes | None = None,
) -> tuple[int, Any]:
  try:
    request_headers = {
      "Accept": "application/vnd.github+json",
      "Authorization": f"Bearer {token}",
      "X-GitHub-Api-Version": GITHUB_API_VERSION,
      "User-Agent": "varda-release-uploader/1.0",
    }
    if headers:
      request_headers.update(headers)

    status, body, _response_headers = http_request(
      method,
      url,
      headers=request_headers,
      json_body=json_body,
      raw_body=raw_body,
      timeout=120,
      retryable_statuses=RETRYABLE_HTTP_STATUSES,
      max_attempts=DEFAULT_GITHUB_API_MAX_ATTEMPTS,
      retry_base_delay=DEFAULT_GITHUB_RETRY_BASE_DELAY,
      retry_label="GitHub API request",
    )
    return status, body
  except HttpRequestError as err:
    raise GitHubApiError(str(err), http_status=err.http_status) from err


def raise_github_api_error(message: str, status: int, body: Any) -> None:
  details = response_body_to_text(body).strip()
  if details:
    raise GitHubApiError(f"{message}: HTTP {status}\n{details}", http_status=status)
  raise GitHubApiError(f"{message}: HTTP {status}", http_status=status)


def get_release_by_tag(token: str, tag: str) -> dict[str, Any] | None:
  repository = GITHUB_REPOSITORY
  url = f"{DEFAULT_GITHUB_API_BASE}{repository_path(repository)}/releases/tags/{quote(tag, safe='')}"
  status, body = github_api_request("GET", url, token)

  if status == 404:
    return None
  if status < 200 or status >= 300:
    raise_github_api_error(f"Failed to fetch GitHub release for tag {tag!r}", status, body)
  if not isinstance(body, dict):
    fail("GitHub release lookup returned an unexpected response.")

  return body


def create_release(
  token: str,
  *,
  tag: str,
  name: str,
  body: str,
  draft: bool,
  prerelease: bool,
) -> dict[str, Any]:
  repository = GITHUB_REPOSITORY
  url = f"{DEFAULT_GITHUB_API_BASE}{repository_path(repository)}/releases"
  status, response = github_api_request(
    "POST",
    url,
    token,
    json_body={
      "tag_name": tag,
      "name": name,
      "body": body,
      "draft": draft,
      "prerelease": prerelease,
    },
  )

  if status < 200 or status >= 300:
    raise_github_api_error(f"Failed to create GitHub release for tag {tag!r}", status, response)
  if not isinstance(response, dict):
    fail("GitHub release creation returned an unexpected response.")

  return response


def list_release_assets(token: str, release: dict[str, Any]) -> list[dict[str, Any]]:
  assets_url = release.get("assets_url")
  if not isinstance(assets_url, str) or not assets_url:
    fail("GitHub release response did not include an assets_url.")

  status, response = github_api_request("GET", assets_url, token)
  if status < 200 or status >= 300:
    raise_github_api_error("Failed to list GitHub release assets", status, response)
  if not isinstance(response, list):
    fail("GitHub release assets response returned an unexpected response.")

  assets: list[dict[str, Any]] = []
  for item in response:
    if isinstance(item, dict):
      assets.append(item)

  return assets


def delete_release_asset(token: str, asset: dict[str, Any]) -> None:
  asset_url = asset.get("url")
  if not isinstance(asset_url, str) or not asset_url:
    fail("GitHub release asset did not include a url.")

  status, response = github_api_request("DELETE", asset_url, token)
  if status == 404:
    return
  if status < 200 or status >= 300:
    raise_github_api_error("Failed to delete GitHub release asset", status, response)


def upload_release_asset(
  token: str,
  release: dict[str, Any],
  asset_path: Path,
) -> dict[str, Any]:
  upload_url = release.get("upload_url")
  if not isinstance(upload_url, str) or not upload_url:
    fail("GitHub release response did not include an upload_url.")

  base_upload_url = upload_url.split("{", 1)[0]
  asset_url = f"{base_upload_url}?{urlencode({'name': asset_path.name})}"
  content_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
  raw_body = asset_path.read_bytes()

  status, response = github_api_request(
    "POST",
    asset_url,
    token,
    headers={"Content-Type": content_type},
    raw_body=raw_body,
  )

  if status < 200 or status >= 300:
    raise_github_api_error(
      f"Failed to upload GitHub release asset {asset_path.name!r}",
      status,
      response,
    )
  if not isinstance(response, dict):
    fail(f"GitHub upload response for {asset_path.name!r} returned an unexpected response.")

  return response


def validate_release_assets(
  asset_paths: list[Path],
  release: dict[str, Any] | None,
  *,
  replace_assets: bool,
  token: str,
) -> list[Path]:
  if release is None:
    return asset_paths

  existing_assets = list_release_assets(token, release)
  existing_by_name = {
    asset_name: asset
    for asset in existing_assets
    if isinstance((asset_name := asset.get("name")), str) and asset_name
  }

  for asset_path in asset_paths:
    existing_asset = existing_by_name.get(asset_path.name)
    if existing_asset is None:
      continue
    if not replace_assets:
      fail(
        f"GitHub release already has an asset named {asset_path.name!r}. "
        "Pass --replace-assets to delete it first."
      )
    delete_release_asset(token, existing_asset)

  return asset_paths


def print_summary(
  *,
  repository: str,
  tag: str,
  name: str,
  draft: bool,
  prerelease: bool,
  asset_paths: list[Path],
) -> None:
  print("GitHub release upload:")
  print(f"  repo:         {repository}")
  print(f"  tag:          {tag}")
  print(f"  name:         {name}")
  print(f"  draft:        {draft}")
  print(f"  prerelease:   {prerelease}")
  print("  assets:")
  for asset_path in asset_paths:
    print(f"    - {asset_path}")


class CurseForgeUploadError(RuntimeError):
  def __init__(self, message: str, *, http_status: int | None = None):
    super().__init__(message)
    self.http_status = http_status


class GitHubApiError(RuntimeError):
  def __init__(self, message: str, *, http_status: int | None = None):
    super().__init__(message)
    self.http_status = http_status


def client_artifact_path(version: str, release_type: str) -> Path:
  return UPLOAD_DIR / f"{PACK_SLUG}-client-{version}-{release_type}.zip"


def prepare_reset_target(target_directory_arg: str | None, target_directory: str | None) -> str | None:
  if target_directory and target_directory_arg:
    fail("Unexpected trailing arguments.")

  return target_directory or target_directory_arg


def refuse_filesystem_root(path: Path) -> None:
  resolved = path.resolve(strict=False)

  if resolved.parent == resolved:
    fail(f"Refusing to use filesystem root as CURSEFORGE_INSTANCE_DIR: {resolved}")


def iter_pack_config_sources(pack_configs_dir: Path) -> list[Path]:
  if not pack_configs_dir.is_dir():
    fail(f"pack-configs folder not found: {pack_configs_dir}")

  return sorted(pack_configs_dir.iterdir())


def add_reset_arguments(parser: argparse.ArgumentParser) -> None:
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
    "--full",
    dest="full_wipe",
    action="store_true",
    help="Delete additional generated Minecraft instance folders and files.",
  )

  parser.add_argument(
    "--full-wipe",
    dest="full_wipe",
    action="store_true",
    help=argparse.SUPPRESS,
  )

  parser.add_argument(
    "-i",
    "--inline",
    action="store_true",
    help="Copy KubeJS and FTB Quests files into the instance without wiping folders.",
  )


def add_prep_arguments(parser: argparse.ArgumentParser) -> None:
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


def add_copy_arguments(parser: argparse.ArgumentParser) -> None:
  del parser


def add_cf_push_arguments(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    "-r",
    "--release-type",
    choices=("release", "beta", "alpha"),
    required=True,
    help="Release type.",
  )

  parser.add_argument(
    "-v",
    "--version",
    required=True,
    help="Version string, example: 1.0.0.",
  )

  parser.add_argument(
    "-c",
    "--changelog",
    required=True,
    help="Plain-text changelog.",
  )

  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print resolved upload metadata without uploading.",
  )


def add_github_push_arguments(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    "-v",
    "--version",
    required=True,
    help="Version string, example: 1.0.0.",
  )

  parser.add_argument(
    "-c",
    "--changelog",
    required=True,
    help="Release body text.",
  )

  parser.add_argument(
    "--tag",
    help="Override the release tag. Default: v<version>.",
  )

  parser.add_argument(
    "--name",
    help="Override the release name. Default: Varda <version>.",
  )

  parser.add_argument(
    "--draft",
    action="store_true",
    help="Create or keep the release as a draft.",
  )

  parser.add_argument(
    "--prerelease",
    action="store_true",
    help="Mark the release as a prerelease.",
  )

  parser.add_argument(
    "--replace-assets",
    action="store_true",
    help="Delete same-name release assets before reuploading them.",
  )

  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print planned GitHub release actions without making API calls.",
  )


def run_reset(args: argparse.Namespace) -> int:
  try:
    target_directory = prepare_reset_target(args.target_directory_arg, args.target_directory)

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
      copy_path(source, destination)

    print()
    print("Modpack reset and synced!")

    return 0
  except (OSError, ValueError) as exc:
    print(exc, file=sys.stderr)
    return 1


def run_prep(args: argparse.Namespace) -> int:
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
      version=version,
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
  server_config_sha1 = sha1_file(server_zip)
  log(f"Created {server_zip}", quiet=args.quiet)

  mods = current_server_mod_entries(minecraft_instance_json, CLIENT_ONLY_PATTERNS)
  neoforge = neoforge_metadata(neoforge_version)
  manifest = build_manifest(
    version=version,
    minecraft_version=minecraft_version,
    neoforge=neoforge,
    server_config_sha1=server_config_sha1,
    mods=mods,
  )

  validate_manifest_against_schema(manifest)
  write_pages_files(docs_dir=DOCS_DIR, manifest=manifest)

  if args.quiet:
    print(client_zip, flush=True)
    print(server_zip, flush=True)
    print(manifest_path, flush=True)
  else:
    log(f"Created {manifest_path}", quiet=args.quiet)

  return 0


def run_copy(args: argparse.Namespace) -> int:
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

      copy_path(source, destination)
      print()

    print("Configs copied into pack-configs/config.")
  except (OSError, ValueError) as exc:
    print(exc, file=sys.stderr)
    return 1

  return 0


def run_cf_push(args: argparse.Namespace) -> int:
  try:
    version = slugify_version(args.version)

  except (OSError, RuntimeError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  try:
    token = "" if args.dry_run else get_curseforge_api_token()
    result = upload_artifact(
      token=token,
      version=version,
      release_type=args.release_type,
      changelog=args.changelog,
      dry_run=args.dry_run,
    )
    if not args.dry_run and (not isinstance(result, dict) or not isinstance(result.get("id"), int)):
      fail("CurseForge client upload response did not include a numeric id.")

  except (OSError, RuntimeError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  if not args.dry_run:
    print("Upload successful.")

  if result:
    print(json.dumps(result, indent=2))

  return 0


def run_github_push(args: argparse.Namespace) -> int:
  try:
    version = slugify_version(args.version)
  except (OSError, RuntimeError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  repository = GITHUB_REPOSITORY
  tag = args.tag or f"v{version}"
  name = args.name or f"Varda {version}"
  prerelease = args.prerelease
  asset_path = server_config_asset_path(version)

  if not asset_path.is_file():
    print(f"error: upload file not found: {asset_path}", file=sys.stderr)
    return 1

  print_summary(
    repository=repository,
    tag=tag,
    name=name,
    draft=args.draft,
    prerelease=prerelease,
    asset_paths=[asset_path],
  )

  if args.dry_run:
    print("Dry run: no GitHub API calls were made.")
    return 0

  try:
    token = get_github_releases_pat()
    release = get_release_by_tag(token, tag)
    if release is None:
      release = create_release(
        token,
        tag=tag,
        name=name,
        body=args.changelog,
        draft=args.draft,
        prerelease=prerelease,
      )

    validated_assets = validate_release_assets(
      [asset_path],
      release,
      replace_assets=args.replace_assets,
      token=token,
    )

    for candidate in validated_assets:
      upload_release_asset(token, release, candidate)

    html_url = release.get("html_url")
    if isinstance(html_url, str) and html_url:
      print(f"Release URL: {html_url}")

  except (OSError, RuntimeError, ValueError, GitHubApiError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  print("GitHub release upload successful.")
  return 0


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
