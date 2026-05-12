#!/usr/bin/env python3

from __future__ import annotations

import argparse
import errno
import http.client
import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

from lib.common import fail, slugify_version
from lib.env import REPO_ROOT, get_curseforge_api_token
from lib.http import request_url_parts, retry_delay_for_attempt as shared_retry_delay_for_attempt


DEFAULT_BASE_URL = "https://minecraft.curseforge.com"
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024  # Increased to 8MB

UPLOAD_DIR = REPO_ROOT / "tmp" / "release"

PACK_SLUG = "varda"
PACK_DISPLAY_NAME = "Varda"

PROJECT_ID = "533644"
DEFAULT_UPLOAD_MAX_ATTEMPTS = 3
DEFAULT_UPLOAD_RETRY_BASE_DELAY = 5
MAX_CURSEFORGE_UPLOAD_SIZE = 500 * 1000 * 1000
# CurseForge game version IDs from /api/game/versions:
# 11779 = Minecraft 1.21.1
# 10150 = NeoForge
GAME_VERSIONS = [11779, 10150]


class CurseForgeUploadError(RuntimeError):
  def __init__(self, message: str, *, http_status: int | None = None):
    super().__init__(message)
    self.http_status = http_status


def client_artifact_path(version: str, release_type: str) -> Path:
  return UPLOAD_DIR / f"{PACK_SLUG}-client-{version}-{release_type}.zip"


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
  except json.JSONDecodeError as err:
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


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Upload the Varda CurseForge client zip only. "
    "Server config ZIPs are published with scripts/gh-upload.py."
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

  return parser.parse_args()


def main() -> int:
  args = parse_args()

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


if __name__ == "__main__":
  raise SystemExit(main())
