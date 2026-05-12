#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import mimetypes
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from lib.common import fail, slugify_version
from lib.env import REPO_ROOT, get_github_releases_pat
from lib.http import HttpRequestError, http_request, response_body_to_text


UPLOAD_DIR = REPO_ROOT / "tmp" / "release"
GITHUB_REPOSITORY = "varda-dev/varda-modpack"
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_GITHUB_API_BASE = "https://api.github.com"
DEFAULT_GITHUB_API_MAX_ATTEMPTS = 3
DEFAULT_GITHUB_RETRY_BASE_DELAY = 5
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


class GitHubApiError(RuntimeError):
  def __init__(self, message: str, *, http_status: int | None = None):
    super().__init__(message)
    self.http_status = http_status


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


def release_tag_for_version(version: str, release_type: str) -> str:
  if release_type == "release":
    return f"v{version}"
  return f"v{version}-{release_type}"


def release_name_for_version(version: str, release_type: str) -> str:
  if release_type == "release":
    return f"Varda {version}"
  return f"Varda {version} {release_type}"


def resolve_server_installer_assets(version: str, release_type: str) -> list[Path]:
  pattern = f"varda-server-installer-{version}-{release_type}-*"
  assets = [
    path
    for path in sorted(UPLOAD_DIR.glob(pattern), key=lambda candidate: candidate.name)
    if path.is_file()
  ]

  if not assets:
    fail(
      "No server installer binaries were found in tmp/release. "
      f"Expected files matching {pattern}."
    )

  return assets


def sha256_file(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as file:
    while True:
      chunk = file.read(1024 * 1024)
      if not chunk:
        break
      digest.update(chunk)
  return digest.hexdigest()


def write_checksums(asset_paths: list[Path]) -> Path:
  checksums_path = UPLOAD_DIR / "checksums.txt"
  checksums_path.parent.mkdir(parents=True, exist_ok=True)

  lines = [
    f"{sha256_file(path)}  {path.name}"
    for path in sorted(asset_paths, key=lambda candidate: candidate.name)
  ]
  checksums_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
  return checksums_path


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
  assets: list[Path],
  release: dict[str, Any] | None,
  *,
  replace_assets: bool,
  token: str,
) -> list[Path]:
  if release is None:
    return assets

  existing_assets = list_release_assets(token, release)
  existing_by_name = {
    asset_name: asset
    for asset in existing_assets
    if isinstance((asset_name := asset.get("name")), str) and asset_name
  }

  for asset_path in assets:
    existing_asset = existing_by_name.get(asset_path.name)
    if existing_asset is None:
      continue
    if not replace_assets:
      fail(
        f"GitHub release already has an asset named {asset_path.name!r}. "
        "Pass --replace-assets to delete it first."
      )
    delete_release_asset(token, existing_asset)

  return assets


def print_summary(
  *,
  repository: str,
  tag: str,
  name: str,
  draft: bool,
  prerelease: bool,
  asset_paths: list[Path],
  checksums_path: Path,
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
  print(f"    - {checksums_path}")


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Upload Varda server installer binaries to GitHub Releases."
  )

  parser.add_argument(
    "-v",
    "--version",
    required=True,
    help="Version string, example: 1.0.0.",
  )

  parser.add_argument(
    "-r",
    "--release-type",
    choices=("alpha", "beta", "release"),
    required=True,
    help="Release type.",
  )

  parser.add_argument(
    "-c",
    "--changelog",
    required=True,
    help="Release body text.",
  )

  parser.add_argument(
    "--tag",
    help="Override the release tag.",
  )

  parser.add_argument(
    "--name",
    help="Override the release name.",
  )

  parser.add_argument(
    "--draft",
    action="store_true",
    help="Create or keep the release as a draft.",
  )

  parser.add_argument(
    "--prerelease",
    action="store_true",
    help="Force the release to be marked as a prerelease.",
  )

  parser.add_argument(
    "--replace-assets",
    action="store_true",
    help="Delete same-name release assets before reuploading them.",
  )

  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Print the planned GitHub release actions without making API calls.",
  )

  return parser.parse_args()


def main() -> int:
  args = parse_args()

  try:
    version = slugify_version(args.version)
  except (OSError, RuntimeError, ValueError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  repository = GITHUB_REPOSITORY
  tag = args.tag or release_tag_for_version(version, args.release_type)
  name = args.name or release_name_for_version(version, args.release_type)
  prerelease = args.prerelease or args.release_type in {"alpha", "beta"}
  asset_paths = resolve_server_installer_assets(version, args.release_type)
  checksums_path = UPLOAD_DIR / "checksums.txt"

  if not args.dry_run:
    write_checksums(asset_paths)

  print_summary(
    repository=repository,
    tag=tag,
    name=name,
    draft=args.draft,
    prerelease=prerelease,
    asset_paths=asset_paths,
    checksums_path=checksums_path,
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
      [*asset_paths, checksums_path],
      release,
      replace_assets=args.replace_assets,
      token=token,
    )

    for asset_path in validated_assets:
      upload_release_asset(token, release, asset_path)

    html_url = release.get("html_url")
    if isinstance(html_url, str) and html_url:
      print(f"Release URL: {html_url}")

  except (OSError, RuntimeError, ValueError, GitHubApiError) as err:
    print(f"error: {err}", file=sys.stderr)
    return 1

  print("GitHub release upload successful.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
