#!/usr/bin/env python3

from __future__ import annotations

import argparse
import errno
import http.client
import json
import mimetypes
import re
import shlex
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

from lib.env import REPO_ROOT, get_curseforge_api_token


DEFAULT_BASE_URL = "https://minecraft.curseforge.com"
UPLOAD_CHUNK_SIZE = 1024 * 1024

UPLOAD_DIR = REPO_ROOT / "tmp"

PACK_SLUG = "varda"
PACK_DISPLAY_NAME = "Varda"

PROJECT_ID = "533644"
DEFAULT_UPLOAD_MAX_ATTEMPTS = 3
DEFAULT_UPLOAD_RETRY_BASE_DELAY = 5
MAX_CURSEFORGE_UPLOAD_SIZE = 500 * 1000 * 1000
# CurseForge game version IDs from /api/game/versions:
# 12735 = Minecraft 1.21.1, gameVersionTypeID 1
# 10150 = NeoForge, gameVersionTypeID 68441
GAME_VERSIONS = [11779, 10150]


class CurseForgeUploadError(RuntimeError):
  def __init__(self, message: str, *, http_status: int | None = None):
    super().__init__(message)
    self.http_status = http_status


def slugify_version(value: str) -> str:
  value = value.strip()

  if not value:
    raise RuntimeError("Version cannot be empty")

  if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
    raise RuntimeError(
      "Version may only contain letters, numbers, dots, underscores, and hyphens"
    )

  return value


def build_artifact_path(
  artifact_type: str,
  version: str,
  release_type: str,
) -> Path:
  if artifact_type not in {"client", "server"}:
    raise RuntimeError(f"Unknown artifact type: {artifact_type}")

  filename = f"{PACK_SLUG}-{artifact_type}-{version}-{release_type}.zip"
  return UPLOAD_DIR / filename


def format_file_size(size: int) -> str:
  return f"{size / 1000 / 1000:.1f} MB"


def validate_upload_file_size(file_path: Path) -> None:
  size = file_path.stat().st_size

  if size > MAX_CURSEFORGE_UPLOAD_SIZE:
    raise RuntimeError(
      "upload file is too large for CurseForge API: "
      f"{file_path} is {format_file_size(size)}; "
      f"limit is {format_file_size(MAX_CURSEFORGE_UPLOAD_SIZE)}. "
      "CurseForge/Cloudflare is likely to reject this with HTTP 413 "
      "Payload Too Large, which may appear as Broken pipe."
    )


def build_metadata(
  *,
  artifact_type: str,
  version: str,
  release_type: str,
  changelog: str,
  parent_file_id: int | None = None,
) -> dict[str, Any]:
  if artifact_type not in {"client", "server"}:
    raise RuntimeError(f"Unknown artifact type: {artifact_type}")

  metadata: dict[str, Any] = {
    "changelog": changelog,
    "changelogType": "text",
    "releaseType": release_type,
    "isMarkedForManualRelease": False,
  }

  if artifact_type == "client":
    metadata["displayName"] = f"{PACK_DISPLAY_NAME} {version}"
    metadata["gameVersions"] = GAME_VERSIONS
    return metadata

  if parent_file_id is None:
    raise RuntimeError("Server uploads require a parent file ID")

  metadata["displayName"] = f"{PACK_DISPLAY_NAME} {version} Server Files"
  metadata["parentFileID"] = parent_file_id
  return metadata


def require_uploaded_file_id(result: dict[str, Any]) -> int:
  file_id = result.get("id")
  if not isinstance(file_id, int):
    raise RuntimeError(
      f"CurseForge upload response did not include numeric id: {result}"
    )
  return file_id


def upload_artifact(
  *,
  token: str,
  artifact_type: str,
  version: str,
  release_type: str,
  changelog: str,
  parent_file_id: int | None,
  dry_run: bool,
) -> dict[str, Any]:
  file_path = build_artifact_path(artifact_type, version, release_type)

  if not file_path.is_file():
    raise RuntimeError(f"upload file not found: {file_path}")

  file_size = file_path.stat().st_size
  validate_upload_file_size(file_path)

  metadata = build_metadata(
    artifact_type=artifact_type,
    version=version,
    release_type=release_type,
    changelog=changelog,
    parent_file_id=parent_file_id,
  )

  print("CurseForge upload:")
  print(f"  project ID:     {PROJECT_ID}")
  print(f"  artifact type:  {artifact_type}")
  print(f"  file:           {file_path}")
  print(f"  file size:      {format_file_size(file_size)}")
  print(f"  display name:   {metadata['displayName']}")
  print(f"  release type:   {release_type}")

  if artifact_type == "client":
    print(f"  game versions:  {metadata['gameVersions']}")
  else:
    if dry_run and metadata["parentFileID"] == 0:
      print("  parent file ID: 0 (dry-run placeholder)")
    else:
      print(f"  parent file ID: {metadata['parentFileID']}")

  print()

  if dry_run:
    print("Metadata:")
    print(json.dumps(metadata, indent=2))
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
  return status >= 500


def retry_delay_for_attempt(
  attempt: int,
  *,
  base_delay: int = DEFAULT_UPLOAD_RETRY_BASE_DELAY,
) -> int:
  return base_delay * attempt


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


def url_request_path(url: str) -> tuple[str, str, str]:
  parsed = urlsplit(url)

  if parsed.scheme not in {"http", "https"}:
    raise RuntimeError(f"Unsupported upload URL scheme: {parsed.scheme}")

  if not parsed.netloc:
    raise RuntimeError(f"Upload URL is missing a host: {url}")

  path = parsed.path or "/"
  if parsed.query:
    path = f"{path}?{parsed.query}"

  return parsed.scheme, parsed.netloc, path


def parse_upload_response(raw: str) -> dict[str, Any]:
  if not raw.strip():
    return {}

  try:
    return json.loads(raw)
  except json.JSONDecodeError as err:
    raise RuntimeError(f"CurseForge upload returned invalid JSON:\n{raw}") from err


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

  scheme, host, path = url_request_path(url)
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

      delay = retry_delay_for_attempt(attempt)
      print(
        f"CurseForge upload failed on attempt {attempt}/{max_attempts}; "
        f"retrying in {delay}s.",
        file=sys.stderr,
      )
      time.sleep(delay)

  assert last_err is not None
  raise last_err


def build_server_retry_command(
  *,
  version: str,
  release_type: str,
  parent_file_id: int,
  changelog: str,
) -> str:
  return (
    "./scripts/cf-upload.py "
    f"-v {shlex.quote(version)} "
    f"-r {shlex.quote(release_type)} "
    f"--server-only "
    f"--parent-file-id {parent_file_id} "
    f"-c {shlex.quote(changelog)}"
  )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Upload Varda client and server files to CurseForge."
  )

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

  target_group = parser.add_mutually_exclusive_group()
  target_group.add_argument(
    "--client-only",
    action="store_true",
    help="Upload only the client artifact.",
  )

  target_group.add_argument(
    "--server-only",
    action="store_true",
    help="Upload only the server artifact.",
  )

  parser.add_argument(
    "--parent-file-id",
    type=int,
    help="Parent CurseForge file ID for server-only uploads.",
  )

  parser.add_argument(
    "--child-upload-delay",
    type=int,
    default=0,
    help="Seconds to wait between client and server uploads.",
  )

  return parser.parse_args()


def main() -> int:
  args = parse_args()

  try:
    version = slugify_version(args.version)

    if args.client_only and args.server_only:
      raise RuntimeError("--client-only and --server-only are mutually exclusive")

    if args.client_only and args.parent_file_id is not None:
      raise RuntimeError("--client-only does not accept --parent-file-id")

    if args.server_only and args.parent_file_id is None:
      raise RuntimeError("--server-only requires --parent-file-id")

    if not args.client_only and not args.server_only and args.parent_file_id is not None:
      raise RuntimeError(
        "Default client+server uploads do not accept --parent-file-id"
      )

  except (OSError, RuntimeError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  if args.client_only:
    package_modes = ["client"]
  elif args.server_only:
    package_modes = ["server"]
  else:
    package_modes = ["client", "server"]

  try:
    token = "" if args.dry_run else get_curseforge_api_token()

    if package_modes == ["client"]:
      result = upload_artifact(
        token=token,
        artifact_type="client",
        version=version,
        release_type=args.release_type,
        changelog=args.changelog,
        parent_file_id=None,
        dry_run=args.dry_run,
      )
    elif package_modes == ["server"]:
      result = upload_artifact(
        token=token,
        artifact_type="server",
        version=version,
        release_type=args.release_type,
        changelog=args.changelog,
        parent_file_id=args.parent_file_id,
        dry_run=args.dry_run,
      )
    else:
      client_result = upload_artifact(
        token=token,
        artifact_type="client",
        version=version,
        release_type=args.release_type,
        changelog=args.changelog,
        parent_file_id=None,
        dry_run=args.dry_run,
      )

      if args.dry_run:
        parent_file_id = 0
      else:
        parent_file_id = require_uploaded_file_id(client_result)

        if args.child_upload_delay > 0:
          print(
            f"Waiting {args.child_upload_delay}s before server upload...",
          )
          time.sleep(args.child_upload_delay)

      try:
        result = upload_artifact(
          token=token,
          artifact_type="server",
          version=version,
          release_type=args.release_type,
          changelog=args.changelog,
          parent_file_id=parent_file_id,
          dry_run=args.dry_run,
        )
      except Exception:
        if not args.dry_run:
          retry_command = build_server_retry_command(
            version=version,
            release_type=args.release_type,
            parent_file_id=parent_file_id,
            changelog=args.changelog,
          )
          print(
            f"Client upload succeeded with file ID {parent_file_id}, but server upload failed.",
            file=sys.stderr,
          )
          print("Retry the server upload with:", file=sys.stderr)
          print(f"  {retry_command}", file=sys.stderr)
        raise

  except (OSError, RuntimeError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  if not args.dry_run:
    print("Upload successful.")

  if result:
    print(json.dumps(result, indent=2))

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
