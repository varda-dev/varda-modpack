from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from lib.common import fail


MANIFEST_SCHEMA_URL = "https://varda-dev.github.io/varda-manifest/manifest.schema.json"
_SCHEMA_CACHE: dict[str, object] | None = None


def fetch_text(url: str) -> str:
  try:
    with urllib.request.urlopen(url, timeout=30) as response:
      return response.read().decode("utf-8", errors="replace")
  except urllib.error.URLError as error:
    fail(f"Could not fetch manifest schema from {url}: {error}")


def parse_json_object(data: str, *, label: str) -> dict[str, object]:
  try:
    parsed = json.loads(data)
  except json.JSONDecodeError as error:
    fail(f"Could not parse JSON from {label}: {error}")

  if not isinstance(parsed, dict):
    fail(f"{label} must contain a JSON object.")

  return parsed


def fetch_manifest_schema() -> dict[str, object]:
  global _SCHEMA_CACHE

  if _SCHEMA_CACHE is None:
    _SCHEMA_CACHE = parse_json_object(
      fetch_text(MANIFEST_SCHEMA_URL),
      label=MANIFEST_SCHEMA_URL,
    )

  return _SCHEMA_CACHE


def _format_path(parts: Iterable[object]) -> str:
  value = ""
  for part in parts:
    if isinstance(part, int):
      value += f"[{part}]"
    else:
      if value:
        value += "."
      value += str(part)

  return value or "<root>"


def format_validation_error(error: Any) -> str:
  path = _format_path(error.path)
  validator = getattr(error, "validator", "<unknown>")
  schema_path = _format_path(error.schema_path)
  message = error.message
  return f"{path}: {message} [validator={validator}, schema_path={schema_path}]"


def validate_manifest_against_schema(manifest: dict[str, object]) -> None:
  schema = fetch_manifest_schema()
  validator = Draft202012Validator(schema, format_checker=FormatChecker())
  errors = sorted(
    validator.iter_errors(manifest),
    key=lambda error: (list(error.path), list(error.schema_path), error.message),
  )

  if not errors:
    return

  lines = ["Manifest validation failed:"]
  lines.extend(f"- {format_validation_error(error)}" for error in errors)
  fail("\n".join(lines))
