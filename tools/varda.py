#!/usr/bin/env python

from __future__ import annotations

import argparse
import sys

from lib.varda_commands import (
  HelpFormatter,
)
from lib.curseforge import add_arguments as add_curseforge_arguments, run as run_curseforge
from lib.copy import add_arguments as add_copy_arguments, run as run_copy
from lib.prep import add_arguments as add_prep_arguments, run as run_prep
from lib.reset import add_arguments as add_reset_arguments, run as run_reset


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description="Varda modpack command-line tools.",
    formatter_class=HelpFormatter,
  )

  subparsers = parser.add_subparsers(dest="command", required=True)

  reset_parser = subparsers.add_parser(
    "reset",
    help="Reset a modpack instance and sync project files into it.",
    description="Reset a modpack instance and sync project files into it.",
    formatter_class=HelpFormatter,
  )
  add_reset_arguments(reset_parser)
  reset_parser.set_defaults(func=run_reset)

  prep_parser = subparsers.add_parser(
    "prep",
    help="Prepare release artifacts.",
    description="Prepare Varda client zip, server config ZIP, and Pages manifest.",
    formatter_class=HelpFormatter,
  )
  add_prep_arguments(prep_parser)
  prep_parser.set_defaults(func=run_prep)

  copy_parser = subparsers.add_parser(
    "copy",
    help="Copy config files from the Minecraft instance into the repository.",
    description="Copy specific config files from the Minecraft instance into the repository.",
    formatter_class=HelpFormatter,
  )
  add_copy_arguments(copy_parser)
  copy_parser.set_defaults(func=run_copy)

  cf_parser = subparsers.add_parser(
    "curseforge",
    help="CurseForge upload commands.",
    description="CurseForge upload commands.",
    formatter_class=HelpFormatter,
  )
  cf_subparsers = cf_parser.add_subparsers(dest="curseforge_command", required=True)
  cf_push_parser = cf_subparsers.add_parser(
    "push",
    help="Upload the CurseForge client ZIP.",
    description=(
      "Upload the Varda CurseForge client zip only. "
      "Server config ZIPs are published to GitHub Releases with the GitHub CLI."
    ),
    formatter_class=HelpFormatter,
  )
  add_curseforge_arguments(cf_push_parser)
  cf_push_parser.set_defaults(func=run_curseforge)

  return parser


def main(argv: list[str] | None = None) -> int:
  parser = build_parser()
  args = parser.parse_args(argv)
  return args.func(args)


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except (OSError, ValueError) as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
