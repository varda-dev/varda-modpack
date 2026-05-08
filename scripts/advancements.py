import argparse
import json
import re
from pathlib import Path
from typing import Any
from zipfile import ZipFile


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PACK_DIR_FILE = REPO_ROOT / "PACK_DIR.txt"
OUTPUT_DIR = REPO_ROOT / "advancements"
DEFAULT_MOD_PATTERNS = ("FarmersDelight-*.jar",)


ADVANCEMENT_RE = re.compile(
    r"^data/(?P<namespace>[^/]+)/advancements?/(?P<path>.+)\.json$"
)
LANG_RE = re.compile(r"^assets/[^/]+/lang/en_us\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract advancement metadata from the vanilla Minecraft jar and "
            "selected mod jars for the instance configured in PACK_DIR.txt."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for generated advancement files.",
    )
    parser.add_argument(
        "--jar",
        type=Path,
        help="Explicit Minecraft jar path. Defaults to the manifest version jar.",
    )
    parser.add_argument(
        "--mod-jar",
        action="append",
        type=Path,
        default=[],
        help="Additional mod jar to extract. Can be passed multiple times.",
    )
    parser.add_argument(
        "--mod-pattern",
        action="append",
        default=[],
        help="Glob under the instance mods directory. Can be passed multiple times.",
    )
    parser.add_argument(
        "--minecraft-only",
        action="store_true",
        help="Only extract the vanilla Minecraft jar.",
    )
    parser.add_argument(
        "--version",
        help="Minecraft version to extract. Defaults to the instance manifest version.",
    )
    parser.add_argument(
        "--include-recipes",
        action="store_true",
        help="Include recipe advancements under */recipes/*. Defaults to false.",
    )
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_pack_dir() -> Path:
    if not PACK_DIR_FILE.exists():
        raise FileNotFoundError(f"Pack directory file not found: {PACK_DIR_FILE}")

    pack_dir = Path(PACK_DIR_FILE.read_text(encoding="utf-8").strip()).expanduser()
    if not pack_dir.exists():
        raise FileNotFoundError(f"Pack directory does not exist: {pack_dir}")

    return pack_dir


def find_minecraft_root(pack_dir: Path) -> Path:
    for path in (pack_dir, *pack_dir.parents):
        if path.name == "minecraft" and (path / "Install").exists():
            return path

    raise FileNotFoundError(
        f"Could not find CurseForge minecraft root above pack directory: {pack_dir}"
    )


def find_manifest(pack_dir: Path) -> Path:
    for path in (pack_dir / "manifest.json", REPO_ROOT / "manifest.json"):
        if path.exists():
            return path

    raise FileNotFoundError(
        f"No manifest.json found in pack directory or repo root: {pack_dir}"
    )


def get_minecraft_version(pack_dir: Path, requested_version: str | None) -> str:
    if requested_version:
        return requested_version

    manifest = read_json(find_manifest(pack_dir))
    try:
        version = manifest["minecraft"]["version"]
    except KeyError as error:
        raise KeyError("manifest.json is missing minecraft.version") from error

    if not isinstance(version, str) or not version:
        raise ValueError("manifest.json minecraft.version must be a non-empty string")

    return version


def find_minecraft_jar(pack_dir: Path, version: str, requested_jar: Path | None) -> Path:
    if requested_jar:
        jar_path = requested_jar.expanduser()
        if not jar_path.exists():
            raise FileNotFoundError(f"Minecraft jar does not exist: {jar_path}")
        return jar_path

    minecraft_root = find_minecraft_root(pack_dir)
    jar_path = minecraft_root / "Install" / "versions" / version / f"{version}.jar"
    if not jar_path.exists():
        raise FileNotFoundError(f"Minecraft jar does not exist: {jar_path}")

    return jar_path


def find_mod_jars(
    pack_dir: Path, patterns: list[str], requested_jars: list[Path]
) -> list[Path]:
    jars = []
    mods_dir = pack_dir / "mods"

    for requested_jar in requested_jars:
        jar_path = requested_jar.expanduser()
        if not jar_path.exists():
            raise FileNotFoundError(f"Mod jar does not exist: {jar_path}")
        jars.append(jar_path)

    if patterns:
        if not mods_dir.exists():
            raise FileNotFoundError(f"Mods directory does not exist: {mods_dir}")

        for pattern in patterns:
            matches = sorted(mods_dir.glob(pattern))
            if not matches:
                raise FileNotFoundError(
                    f"No mod jars matched pattern {pattern!r} in {mods_dir}"
                )
            jars.extend(matches)

    return sorted(set(jars))


def read_zip_json(zip_file: ZipFile, name: str) -> Any:
    with zip_file.open(name) as file:
        return json.load(file)


def load_translations(zip_file: ZipFile) -> dict[str, str]:
    merged = {}

    for name in sorted(zip_file.namelist()):
        if not LANG_RE.match(name):
            continue

        translations = read_zip_json(zip_file, name)
        if isinstance(translations, dict):
            merged.update({str(key): str(value) for key, value in translations.items()})

    return merged


def format_text(value: Any, translations: dict[str, str]) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(format_text(part, translations) or "" for part in value)
    if not isinstance(value, dict):
        return str(value)

    if "text" in value:
        return str(value["text"])

    if "translate" in value:
        key = str(value["translate"])
        translated = translations.get(key, key)
        with_values = value.get("with")
        if isinstance(with_values, list):
            replacements = tuple(format_text(item, translations) or "" for item in with_values)
            try:
                return translated % replacements
            except (TypeError, ValueError):
                return translated
        return translated

    extra = value.get("extra")
    if isinstance(extra, list):
        return "".join(format_text(part, translations) or "" for part in extra)

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def advancement_id(zip_path: str) -> str:
    match = ADVANCEMENT_RE.match(zip_path)
    if not match:
        raise ValueError(f"Not an advancement path: {zip_path}")
    return f"{match.group('namespace')}:{match.group('path')}"


def category_from_id(identifier: str) -> str:
    path = identifier.split(":", 1)[1]
    return path.split("/", 1)[0] if "/" in path else ""


def should_include(path: str, include_recipes: bool) -> bool:
    if include_recipes:
        return True

    match = ADVANCEMENT_RE.match(path)
    return bool(match and not match.group("path").startswith("recipes/"))


def icon_id(display: dict[str, Any]) -> str | None:
    icon = display.get("icon")
    if isinstance(icon, dict):
        item_id = icon.get("id") or icon.get("item")
        return str(item_id) if item_id else None
    return None


def make_record(
    jar_path: Path,
    zip_path: str,
    data: dict[str, Any],
    translations: dict[str, str],
) -> dict[str, Any]:
    identifier = advancement_id(zip_path)
    display = data.get("display")
    display = display if isinstance(display, dict) else {}
    criteria = data.get("criteria")
    criteria = criteria if isinstance(criteria, dict) else {}

    return {
        "id": identifier,
        "namespace": identifier.split(":", 1)[0],
        "path": identifier.split(":", 1)[1],
        "category": category_from_id(identifier),
        "title": format_text(display.get("title"), translations),
        "description": format_text(display.get("description"), translations),
        "parent": data.get("parent"),
        "display": {
            "icon": icon_id(display),
            "frame": display.get("frame", "task") if display else None,
            "hidden": display.get("hidden", False) if display else None,
            "show_toast": display.get("show_toast", True) if display else None,
            "announce_to_chat": display.get("announce_to_chat", True) if display else None,
            "background": display.get("background"),
            "raw": display or None,
        },
        "criteria": criteria,
        "criteria_count": len(criteria),
        "requirements": data.get("requirements", []),
        "rewards": data.get("rewards", {}),
        "sends_telemetry_event": data.get("sends_telemetry_event", False),
        "source": {
            "archive": str(jar_path),
            "path": zip_path,
        },
        "raw": data,
    }


def collect_advancements(
    jar_path: Path, include_recipes: bool
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = []
    skipped = 0

    with ZipFile(jar_path) as zip_file:
        names = zip_file.namelist()
        translations = load_translations(zip_file)

        for name in sorted(names):
            if not ADVANCEMENT_RE.match(name):
                continue
            if not should_include(name, include_recipes):
                skipped += 1
                continue

            data = read_zip_json(zip_file, name)
            if not isinstance(data, dict):
                raise ValueError(f"Expected advancement JSON object in {name}")

            records.append(make_record(jar_path, name, data, translations))

    meta = {
        "source_archive": str(jar_path),
        "advancement_count": len(records),
        "skipped_recipe_advancement_count": skipped,
        "include_recipes": include_recipes,
    }
    return records, meta


def output_slug(records: list[dict[str, Any]], fallback: str) -> str:
    namespaces = sorted({record["namespace"] for record in records})
    if len(namespaces) == 1:
        return namespaces[0]

    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", fallback.lower()).strip("_")
    return slug or "unknown"


def output_title(source_slug: str) -> str:
    titles = {
        "farmersdelight": "Farmer's Delight",
        "minecraft": "Minecraft",
    }
    return titles.get(source_slug, source_slug)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def criteria_summary(record: dict[str, Any]) -> str:
    criteria = record["criteria"]
    requirements = record["requirements"]
    if not criteria:
        return "none"

    if requirements:
        group_count = len(requirements)
        criterion_count = len(criteria)
        if group_count == criterion_count and all(len(group) == 1 for group in requirements):
            return f"{criterion_count} required"
        return f"{criterion_count} criteria across {group_count} requirement groups"

    return f"{len(criteria)} criteria"


def write_markdown(
    path: Path,
    title: str,
    version: str,
    meta: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title} Advancements",
        "",
        f"Minecraft version: `{version}`",
        f"Source: `{meta['source_archive']}`",
        f"Count: {meta['advancement_count']}",
        "",
    ]

    current_category = None
    for record in records:
        if record["category"] != current_category:
            current_category = record["category"]
            lines.extend(["", f"## {current_category or 'uncategorized'}", ""])

        title = record["title"] or record["id"]
        description = record["description"] or ""
        parent = record["parent"] or "none"
        icon = record["display"]["icon"] or "none"
        lines.extend(
            [
                f"### {title}",
                "",
                f"- ID: `{record['id']}`",
                f"- Description: {description}",
                f"- Parent: `{parent}`",
                f"- Icon: `{icon}`",
                f"- Frame: `{record['display']['frame']}`",
                f"- Requirements: {criteria_summary(record)}",
                "",
            ]
        )

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_outputs(
    output_dir: Path,
    version: str,
    source_slug: str,
    title: str,
    records: list[dict[str, Any]],
    meta: dict[str, Any],
) -> list[Path]:
    base_dir = output_dir / source_slug / version
    payload = {"meta": meta, "advancements": records}
    by_id = {record["id"]: record for record in records}
    counts_by_category: dict[str, int] = {}

    for record in records:
        category = record["category"] or "uncategorized"
        counts_by_category[category] = counts_by_category.get(category, 0) + 1

    index = {
        **meta,
        "minecraft_version": version,
        "source_slug": source_slug,
        "counts_by_category": dict(sorted(counts_by_category.items())),
        "advancement_ids": [record["id"] for record in records],
    }

    files = [
        base_dir / "advancements.json",
        base_dir / "advancements_by_id.json",
        base_dir / "index.json",
        base_dir / "README.md",
    ]
    write_json(files[0], payload)
    write_json(files[1], by_id)
    write_json(files[2], index)
    write_markdown(files[3], title, version, meta, records)
    return files


def extract_archive(
    output_dir: Path,
    version: str,
    jar_path: Path,
    source_slug: str | None,
    title: str | None,
    include_recipes: bool,
) -> tuple[list[dict[str, Any]], list[Path]]:
    records, meta = collect_advancements(jar_path, include_recipes)
    resolved_slug = source_slug or output_slug(records, jar_path.stem)
    resolved_title = title or output_title(resolved_slug)
    files = write_outputs(
        output_dir, version, resolved_slug, resolved_title, records, meta
    )
    return records, files


def main() -> int:
    args = parse_args()
    pack_dir = read_pack_dir()
    version = get_minecraft_version(pack_dir, args.version)
    minecraft_jar = find_minecraft_jar(pack_dir, version, args.jar)
    archives: list[tuple[Path, str | None, str | None]] = [
        (minecraft_jar, "minecraft", f"Minecraft {version}"),
    ]

    if not args.minecraft_only:
        mod_patterns = args.mod_pattern or list(DEFAULT_MOD_PATTERNS)
        for mod_jar in find_mod_jars(pack_dir, mod_patterns, args.mod_jar):
            archives.append((mod_jar, None, None))

    for jar_path, source_slug, title in archives:
        records, files = extract_archive(
            args.output_dir,
            version,
            jar_path,
            source_slug,
            title,
            args.include_recipes,
        )

        print(f"Extracted {len(records)} advancements from {jar_path}")
        for path in files:
            print(path.relative_to(REPO_ROOT))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
