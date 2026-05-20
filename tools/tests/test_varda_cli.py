from __future__ import annotations

import io
import importlib.util
import sys
import unittest
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

ROOT_DIR = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT_DIR / "tools"
VARDA_PATH = TOOLS_DIR / "varda.py"

if str(TOOLS_DIR) not in sys.path:
  sys.path.insert(0, str(TOOLS_DIR))

spec = importlib.util.spec_from_file_location("varda_cli", VARDA_PATH)
if spec is None or spec.loader is None:
  raise RuntimeError(f"Could not load {VARDA_PATH}")

varda_cli = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = varda_cli
spec.loader.exec_module(varda_cli)

from lib import varda_commands


class VardaCliTests(unittest.TestCase):
  def assert_help(self, parser, args: list[str], needles: list[str]) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
      with self.assertRaises(SystemExit) as ctx:
        parser.parse_args(args)

    self.assertEqual(ctx.exception.code, 0)
    output = stdout.getvalue() + stderr.getvalue()
    for needle in needles:
      self.assertIn(needle, output)

  def test_master_parser_accepts_full_aliases(self) -> None:
    parser = varda_cli.build_parser()

    args = parser.parse_args(["reset", "--full"])
    self.assertTrue(args.full_wipe)

    args = parser.parse_args(["reset", "--full-wipe"])
    self.assertTrue(args.full_wipe)

  def test_master_help(self) -> None:
    self.assert_help(
      varda_cli.build_parser(),
      ["-h"],
      needles=["reset", "prep", "copy", "curseforge"],
    )

  def test_master_reset_help(self) -> None:
    self.assert_help(
      varda_cli.build_parser(),
      ["reset", "-h"],
      needles=["INSTANCE_DIR", "--full", "--inline"],
    )

  def test_master_prep_help(self) -> None:
    self.assert_help(
      varda_cli.build_parser(),
      ["prep", "-h"],
      needles=["--version", "--quiet", "--verbose"],
    )

  def test_master_copy_help(self) -> None:
    self.assert_help(
      varda_cli.build_parser(),
      ["copy", "-h"],
      needles=["Copy specific config files"],
    )

  def test_master_cf_help(self) -> None:
    self.assert_help(
      varda_cli.build_parser(),
      ["curseforge", "-h"],
      needles=["push"],
    )

  def test_master_cf_push_help(self) -> None:
    self.assert_help(
      varda_cli.build_parser(),
      ["curseforge", "push", "-h"],
      needles=["--release-type", "--changelog"],
    )

  def test_generated_paths_are_repo_rooted(self) -> None:
    self.assertEqual(varda_commands.TMP_DIR, ROOT_DIR / "tmp")
    self.assertEqual(varda_commands.DOCS_DIR, ROOT_DIR / "docs")
    self.assertEqual(
      varda_commands.client_zip_path("0.1.16", "beta"),
      ROOT_DIR / "tmp" / "release" / "varda-client-0.1.16-beta.zip",
    )
    self.assertEqual(
      varda_commands.server_config_zip_path("0.1.16"),
      ROOT_DIR / "tmp" / "release" / "varda-server-config-0.1.16.zip",
    )

if __name__ == "__main__":
  unittest.main()
