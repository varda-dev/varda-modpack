from __future__ import annotations

import json
import urllib.error
import urllib.request
import re
from collections.abc import Iterable
from typing import Any

try:
  from jsonschema import Draft202012Validator, FormatChecker
except ModuleNotFoundError:
  class FormatChecker:
    pass


  class _FallbackValidationError:
    def __init__(
      self,
      message: str,
      *,
      path: tuple[object, ...] = (),
      schema_path: tuple[object, ...] = (),
      validator: str = "<unknown>",
    ) -> None:
      self.message = message
      self.path = path
      self.schema_path = schema_path
      self.validator = validator


  def _type_matches(instance: Any, expected: str) -> bool:
    if expected == "object":
      return isinstance(instance, dict)
    if expected == "array":
      return isinstance(instance, list)
    if expected == "string":
      return isinstance(instance, str)
    if expected == "integer":
      return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
      return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
      return isinstance(instance, bool)
    if expected == "null":
      return instance is None
    return True


  def _fallback_iter_errors(
    instance: Any,
    schema: dict[str, object],
    *,
    path: tuple[object, ...] = (),
    schema_path: tuple[object, ...] = (),
  ) -> list[_FallbackValidationError]:
    errors: list[_FallbackValidationError] = []

    schema_type = schema.get("type")
    if isinstance(schema_type, str) and not _type_matches(instance, schema_type):
      errors.append(
        _FallbackValidationError(
          f"{instance!r} is not of type {schema_type!r}",
          path=path,
          schema_path=schema_path + ("type",),
          validator="type",
        )
      )
      return errors

    if isinstance(instance, dict):
      required = schema.get("required")
      if isinstance(required, list):
        for key in required:
          if isinstance(key, str) and key not in instance:
            errors.append(
              _FallbackValidationError(
                f"'{key}' is a required property",
                path=path,
                schema_path=schema_path + ("required",),
                validator="required",
              )
            )

      properties = schema.get("properties")
      if isinstance(properties, dict):
        for key, child_schema in properties.items():
          if key in instance and isinstance(child_schema, dict):
            errors.extend(
              _fallback_iter_errors(
                instance[key],
                child_schema,
                path=path + (key,),
                schema_path=schema_path + ("properties", key),
              )
            )

    if isinstance(instance, list):
      items = schema.get("items")
      if isinstance(items, dict):
        for index, value in enumerate(instance):
          errors.extend(
            _fallback_iter_errors(
              value,
              items,
              path=path + (index,),
              schema_path=schema_path + ("items",),
            )
          )

    if isinstance(instance, str):
      pattern = schema.get("pattern")
      if isinstance(pattern, str) and re.search(pattern, instance) is None:
        errors.append(
          _FallbackValidationError(
            f"{instance!r} does not match {pattern!r}",
            path=path,
            schema_path=schema_path + ("pattern",),
            validator="pattern",
          )
        )

    return errors


  class Draft202012Validator:
    def __init__(self, schema: dict[str, object], format_checker: FormatChecker | None = None) -> None:
      self.schema = schema

    def iter_errors(self, instance: Any):
      yield from _fallback_iter_errors(instance, self.schema)

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
