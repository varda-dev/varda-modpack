#!/usr/bin/env python3

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

from lib import REPO_ROOT, get_curseforge_api_token


DEFAULT_BASE_URL = "https://minecraft.curseforge.com"
UPLOAD_CHUNK_SIZE = 1024 * 1024

UPLOAD_DIR = REPO_ROOT / "tmp"

PACK_SLUG = "varda"
PACK_DISPLAY_NAME = "Varda"
ARTIFACT_TYPE = "client"

PROJECT_ID = "533644"
GAME_VERSIONS = [12735, 10150]


def slugify_version(value: str) -> str:
  value = value.strip()

  if not value:
    raise RuntimeError("Version cannot be empty")

  if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
    raise RuntimeError(
      "Version may only contain letters, numbers, dots, underscores, and hyphens"
    )

  return value


def build_artifact_path(version: str, release_type: str) -> Path:
  filename = f"{PACK_SLUG}-{ARTIFACT_TYPE}-{version}-{release_type}.zip"
  return UPLOAD_DIR / filename


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


def upload_file(
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
      raise RuntimeError(
        f"CurseForge upload failed: HTTP {response.status} {response.reason}\n{raw}"
      )

    return parse_upload_response(raw)

  except (OSError, http.client.HTTPException) as err:
    raise RuntimeError(f"CurseForge upload failed: {err}") from err

  finally:
    if connection is not None:
      connection.close()


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Upload a CurseForge Minecraft client modpack zip."
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

  file_path = build_artifact_path(version, args.release_type)

  if not file_path.is_file():
    print(f"error: upload file not found: {file_path}", file=sys.stderr)
    return 1

  display_name = f"{PACK_DISPLAY_NAME} {version}"

  metadata: dict[str, Any] = {
    "changelog": args.changelog,
    "changelogType": "text",
    "displayName": display_name,
    "gameVersions": GAME_VERSIONS,
    "releaseType": args.release_type,
    "isMarkedForManualRelease": False,
  }

  print("CurseForge upload:")
  print(f"  project ID:     {PROJECT_ID}")
  print(f"  file:           {file_path}")
  print(f"  display name:   {display_name}")
  print(f"  release type:   {args.release_type}")
  print(f"  game versions:  {GAME_VERSIONS}")
  print()

  if args.dry_run:
    print("Metadata:")
    print(json.dumps(metadata, indent=2))
    return 0

  try:
    token = get_curseforge_api_token()
    result = upload_file(
      base_url=DEFAULT_BASE_URL,
      token=token,
      project_id=PROJECT_ID,
      file_path=file_path,
      metadata=metadata,
    )
  except (OSError, RuntimeError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  print("Upload successful.")

  if result:
    print(json.dumps(result, indent=2))

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
