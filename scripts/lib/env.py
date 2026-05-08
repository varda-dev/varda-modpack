#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ENV_PATH = REPO_ROOT / ".env"
CURSEFORGE_INSTANCE_DIR = "CURSEFORGE_INSTANCE_DIR"
CURSEFORGE_API_TOKEN = "CURSEFORGE_API_TOKEN"


def load_dotenv(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
  if not path.is_file():
    raise FileNotFoundError(f"Missing .env file: {path}")

  values: dict[str, str] = {}

  for line in path.read_text(encoding="utf-8").splitlines():
    line = line.strip()

    if not line or line.startswith("#") or "=" not in line:
      continue

    if line.startswith("export "):
      line = line[len("export ") :].strip()

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
      value = value[1:-1]

    if key:
      values[key] = value

  return values


def env_required(values: dict[str, str], name: str) -> str:
  value = values.get(name, "").strip()

  if not value:
    raise ValueError(f"Missing required .env value: {name}")

  return value


def env_path_required(
  values: dict[str, str],
  name: str,
  *,
  must_be_dir: bool = False,
) -> Path:
  raw_path = env_required(values, name)

  try:
    path = Path(raw_path).expanduser().resolve(strict=False)
  except RuntimeError as exc:
    raise ValueError(f"Could not expand home directory in {name}: {raw_path}") from exc

  if must_be_dir and not path.is_dir():
    raise NotADirectoryError(f"{name} does not exist or is not a directory: {path}")

  if not must_be_dir and not path.exists():
    raise FileNotFoundError(f"{name} does not exist: {path}")

  return path.resolve()


def get_curseforge_instance_dir() -> Path:
  return env_path_required(
    load_dotenv(),
    CURSEFORGE_INSTANCE_DIR,
    must_be_dir=True,
  )


def get_curseforge_api_token() -> str:
  return env_required(load_dotenv(), CURSEFORGE_API_TOKEN)
