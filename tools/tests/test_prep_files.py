from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import types
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT_DIR / "tools"
SCRIPT_PATH = TOOLS_DIR / "prep-files.py"

if "jsonschema" not in sys.modules:
  try:
    import jsonschema  # type: ignore  # noqa: F401
  except ModuleNotFoundError:
    jsonschema_stub = types.ModuleType("jsonschema")

    class _Draft202012Validator:
      def __init__(self, *args, **kwargs) -> None:
        pass

      def iter_errors(self, instance):
        return []

    class _FormatChecker:
      pass

    jsonschema_stub.Draft202012Validator = _Draft202012Validator
    jsonschema_stub.FormatChecker = _FormatChecker
    sys.modules["jsonschema"] = jsonschema_stub

if str(TOOLS_DIR) not in sys.path:
  sys.path.insert(0, str(TOOLS_DIR))

spec = importlib.util.spec_from_file_location("prep_files", SCRIPT_PATH)
if spec is None or spec.loader is None:
  raise RuntimeError(f"Could not load {SCRIPT_PATH}")

prep_files = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prep_files
spec.loader.exec_module(prep_files)


class PrepFilesTests(unittest.TestCase):
  def test_copy_client_manifest_refreshes_loader_and_version(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir_raw:
      temp_dir = Path(temp_dir_raw)
      instance_dir = temp_dir / "instance"
      package_dir = temp_dir / "package"

      instance_dir.mkdir()
      package_dir.mkdir()

      (instance_dir / "manifest.json").write_text(
        json.dumps(
          {
            "version": "0.1.13",
            "minecraft": {
              "version": "1.21.1",
              "modLoaders": [
                {
                  "id": "neoforge-21.1.228",
                  "primary": True,
                }
              ],
            },
            "overrides": "old-overrides",
            "files": [],
          }
        ),
        encoding="utf-8",
      )

      (instance_dir / "minecraftinstance.json").write_text(
        json.dumps(
          {
            "gameVersion": "1.21.1",
            "baseModLoader": {
              "forgeVersion": "21.1.229",
            },
            "installedAddons": [
              {
                "addonID": 123,
                "isEnabled": True,
                "installedFile": {
                  "id": 456,
                  "projectId": 123,
                  "fileName": "example-1.0.0.jar",
                },
              }
            ],
          }
        ),
        encoding="utf-8",
      )

      prep_files.copy_client_manifest(
        instance_dir=instance_dir,
        package_dir=package_dir,
        server_only_patterns=[],
        version="0.1.14",
      )

      manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))

      self.assertEqual(manifest["version"], "0.1.14")
      self.assertEqual(
        manifest["minecraft"],
        {
          "version": "1.21.1",
          "modLoaders": [
            {
              "id": "neoforge-21.1.229",
              "primary": True,
            }
          ],
        },
      )
      self.assertEqual(
        manifest["files"],
        [
          {
            "projectID": 123,
            "fileID": 456,
            "required": True,
          }
        ],
      )
      self.assertNotIn("neoforge-21.1.228", json.dumps(manifest))


if __name__ == "__main__":
  unittest.main()
