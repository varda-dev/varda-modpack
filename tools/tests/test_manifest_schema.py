from __future__ import annotations

import json
import io
import sys
import unittest
from pathlib import Path
from contextlib import redirect_stderr
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT_DIR / "tools"
if str(TOOLS_DIR) not in sys.path:
  sys.path.insert(0, str(TOOLS_DIR))

from lib import manifest_schema


class FakeResponse:
  def __init__(self, body: str) -> None:
    self._body = body.encode("utf-8")

  def __enter__(self) -> FakeResponse:
    return self

  def __exit__(self, exc_type, exc, tb) -> None:
    return None

  def read(self) -> bytes:
    return self._body


class ManifestSchemaTests(unittest.TestCase):
  def setUp(self) -> None:
    manifest_schema._SCHEMA_CACHE = None

  def tearDown(self) -> None:
    manifest_schema._SCHEMA_CACHE = None

  def test_validate_manifest_against_schema(self) -> None:
    schema = {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "type": "object",
      "required": ["version", "schema_version", "minecraft", "loader", "server_config", "mods"],
      "properties": {
        "version": {"type": "string"},
        "schema_version": {"type": "integer"},
        "minecraft": {"type": "string"},
        "loader": {
          "type": "object",
          "required": ["type", "version", "installer_url", "sha1"],
          "properties": {
            "type": {"type": "string"},
            "version": {"type": "string"},
            "installer_url": {
              "type": "string",
              "pattern": r"^https://.+\.jar$",
            },
            "sha1": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
          },
        },
        "server_config": {
          "type": "object",
          "required": ["url", "sha1"],
          "properties": {
            "url": {
              "type": "string",
              "pattern": r"^https://.+\.zip(?:[?#].*)?$",
            },
            "sha1": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
          },
        },
        "mods": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "website_url": {
                "type": "string",
                "pattern": r"^https://.+",
              },
            },
          },
        },
      },
    }

    manifest = {
      "version": "0.1.12",
      "schema_version": 1,
      "minecraft": "1.21.1",
      "loader": {
        "type": "neoforge",
        "version": "21.1.229",
        "installer_url": "https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.229/neoforge-21.1.229-installer.jar",
        "sha1": "7b6f8512bb5f6a2c5d83e3385016da9813d3589b",
      },
      "server_config": {
        "url": "https://example.com/server-config.zip",
        "sha1": "0123456789abcdef0123456789abcdef01234567",
      },
      "mods": [
        {"website_url": "https://example.com/mod"},
      ],
    }

    invalid_manifest = json.loads(json.dumps(manifest))
    invalid_manifest["mods"][0]["website_url"] = "not a url"
    invalid_manifest["server_config"]["url"] = "still not a url"

    response = FakeResponse(json.dumps(schema))
    with patch(
      "lib.manifest_schema.urllib.request.urlopen",
      return_value=response,
    ):
      manifest_schema.validate_manifest_against_schema(manifest)

    with patch(
      "lib.manifest_schema.urllib.request.urlopen",
      return_value=FakeResponse(json.dumps(schema)),
    ):
      stderr = io.StringIO()
      with redirect_stderr(stderr):
        with self.assertRaises(SystemExit):
          manifest_schema.validate_manifest_against_schema(invalid_manifest)

    message = stderr.getvalue()
    self.assertIn("Manifest validation failed:", message)
    self.assertIn("mods[0].website_url", message)
    self.assertIn("server_config.url", message)


if __name__ == "__main__":
  unittest.main()
