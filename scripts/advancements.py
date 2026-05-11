#!/usr/bin/env python3

from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import json
import re
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from lib.common import fail, read_json, write_json
from lib.env import get_curseforge_instance_dir


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = REPO_ROOT / "tmp/advancements"
LOCALES_PATH = SCRIPT_DIR / "lib" / "locales.json"
DEFAULT_MOD_PATTERNS = (
  "ars_additions-*.jar",
  "ars_affinity-*.jar",
  "ars_elemental-*.jar",
  "ars_nouveau-*.jar",
  "endrem-neoforge-*.jar",
  "FarmersDelight-*.jar",
  "HopoBetterRuinedPortals-*.jar",
  "HopoBetterUnderwaterRuins-*.jar",
  "L_Ender's Cataclysm*.jar",
  "mowziesmobs-*.jar",
  "occultism-*.jar",
  "starbunclemania-*.jar",
  "YungsBetterDungeons-*.jar",
  "YungsBetterDesertTemples-*.jar",
  "YungsBetterNetherFortresses-*.jar",
  "YungsBetterStrongholds-*.jar",
)
OUTPUT_TITLES = {
  "ars_additions": "Ars Additions",
  "ars_affinity": "Ars Affinity",
  "ars_elemental": "Ars Elemental",
  "ars_nouveau": "Ars Nouveau",
  "betterdeserttemples": "YUNG's Better Desert Temples",
  "betterdungeons": "YUNG's Better Dungeons",
  "cataclysm": "L_Ender's Cataclysm",
  "endrem": "End Remastered",
  "farmersdelight": "Farmer's Delight",
  "hopo": "Hopo",
  "minecraft": "Minecraft",
  "mowziesmobs": "Mowzie's Mobs",
  "occultism": "Occultism",
  "starbunclemania": "Starbunclemania",
}
DEFAULT_MOD_OUTPUTS = {
  "ars_elemental-*.jar": ("ars_elemental", None),
  "HopoBetterRuinedPortals-*.jar": (
    "hopo_better_ruined_portals",
    "Hopo Better Ruined Portals",
  ),
  "HopoBetterUnderwaterRuins-*.jar": (
    "hopo_better_underwater_ruins",
    "Hopo Better Underwater Ruins",
  ),
  "starbunclemania-*.jar": ("starbunclemania", None),
  "YungsBetterNetherFortresses-*.jar": (
    "betterfortresses",
    "YUNG's Better Nether Fortresses",
  ),
  "YungsBetterStrongholds-*.jar": (
    "betterstrongholds",
    "YUNG's Better Strongholds",
  ),
}
DEFAULT_LOCALES = (
  "en_us",
  "de_de",
  "es_es",
  "fr_fr",
  "pt_br",
  "ru_ru",
  "es_mx",
  "ja_jp",
  "ko_kr",
)

ADVANCEMENT_RE = re.compile(
    r"^data/(?P<namespace>[^/]+)/advancements?/(?P<path>.+)\.json$"
)
LANG_RE = re.compile(r"^assets/(?P<namespace>[^/]+)/lang/(?P<locale>[a-z0-9_-]+)\.json$")

VALID_LOCALES: frozenset[str] | None = None


def normalize_locale_code(locale: str) -> str:
    return locale.strip().lower().replace("-", "_")


def get_valid_locales() -> frozenset[str]:
    global VALID_LOCALES
    if VALID_LOCALES is not None:
        return VALID_LOCALES

    data = read_json(LOCALES_PATH)
    if not isinstance(data, list):
        fail(f"Expected locale list in {LOCALES_PATH}")

    valid = set(DEFAULT_LOCALES)
    for entry in data:
        if not isinstance(entry, dict):
            continue
        locale = entry.get("locale")
        if isinstance(locale, str) and locale.strip():
            valid.add(normalize_locale_code(locale))

    VALID_LOCALES = frozenset(valid)
    return VALID_LOCALES


def parse_locale_arg(locale: str) -> str:
    normalized = normalize_locale_code(locale)
    if normalized in get_valid_locales():
        return normalized

    raise argparse.ArgumentTypeError(
        f"invalid locale {locale!r}; expected a locale from {LOCALES_PATH}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract displayed advancement metadata from the vanilla Minecraft "
            "jar and default mod jars for the instance configured in .env."
        )
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=OUTPUT_DIR,
        dest="output_dir",
        help="Directory for generated advancement files.",
    )
    parser.add_argument(
        "-j",
        "--jar",
        type=Path,
        help=(
            "Extract only this jar. Defaults to the vanilla Minecraft jar and "
            "default mod jars."
        ),
    )
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        help=(
            "With --jar, check whether the jar has displayed advancements "
            "that can be extracted without writing output files."
        ),
    )
    parser.add_argument(
        "-d",
        "--discover",
        action="store_true",
        help=(
            "Scan the configured CurseForge instance mods directory for jars "
            "with displayed advancements that are not already covered by "
            "DEFAULT_MOD_PATTERNS. Prints only matching jar filenames."
        ),
    )
    parser.add_argument(
        "-l",
        "--locale",
        action="append",
        dest="locales",
        metavar="LOCALE",
        type=parse_locale_arg,
        help=(
            "Locale to include in generated metadata. Can be passed multiple "
            "times. Accepts locales from scripts/lib/locales.json. Defaults "
            "to the pack-supported locales."
        ),
    )
    args = parser.parse_args()
    if args.test and not args.jar:
        parser.error("--test requires --jar")
    if args.discover and args.jar:
        parser.error("--discover cannot be used with --jar")
    if args.discover and args.test:
        parser.error("--discover cannot be used with --test")
    return args


def find_minecraft_root(instance_dir: Path) -> Path:
    # Check parent directories for common CurseForge layout
    for path in (instance_dir, *instance_dir.parents):
        if path.name == "minecraft" and (path / "Install").exists():
            return path

    # Check common system paths if instance discovery fails
    # This is a bit speculative but helps in non-standard setups
    home = Path.home()
    common_roots = [
        home / "curseforge/minecraft",
        home / "AppData/Roaming/curseforge/minecraft",
        home / ".local/share/curseforge/minecraft",
    ]
    for root in common_roots:
        if root.exists() and (root / "Install").exists():
            return root

    fail(f"Could not find CurseForge minecraft root above instance directory: {instance_dir}")


def find_manifest(instance_dir: Path) -> Path:
    for path in (instance_dir / "manifest.json", REPO_ROOT / "manifest.json"):
        if path.exists():
            return path

    fail(f"No manifest.json found in instance directory or repo root: {instance_dir}")


def get_minecraft_version(instance_dir: Path) -> str:
    manifest = read_json(find_manifest(instance_dir))
    try:
        version = manifest["minecraft"]["version"]
    except KeyError as error:
        fail("manifest.json is missing minecraft.version")

    if not isinstance(version, str) or not version:
        fail("manifest.json minecraft.version must be a non-empty string")

    return version


def find_minecraft_jar(instance_dir: Path, version: str) -> Path:
    minecraft_root = find_minecraft_root(instance_dir)
    jar_path = minecraft_root / "Install" / "versions" / version / f"{version}.jar"
    if not jar_path.exists():
        fail(f"Minecraft jar does not exist: {jar_path}")

    return jar_path


def find_minecraft_install(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        if (candidate / "assets" / "indexes").exists() and (
            candidate / "assets" / "objects"
        ).exists():
            return candidate
        install_dir = candidate / "Install"
        if (install_dir / "assets" / "indexes").exists() and (
            install_dir / "assets" / "objects"
        ).exists():
            return install_dir

    return None


def find_asset_index_path(jar_path: Path, minecraft_install: Path | None) -> Path | None:
    if minecraft_install is None:
        return None

    version_json = jar_path.with_suffix(".json")
    if version_json.exists():
        version = read_json(version_json)
        asset_index = version.get("assetIndex")
        if isinstance(asset_index, dict):
            asset_index_id = asset_index.get("id")
            if isinstance(asset_index_id, str) and asset_index_id:
                index_path = minecraft_install / "assets" / "indexes" / f"{asset_index_id}.json"
                if index_path.exists():
                    return index_path

    indexes_dir = minecraft_install / "assets" / "indexes"
    indexes = sorted(
        indexes_dir.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return indexes[0] if indexes else None


def find_default_mod_jars(instance_dir: Path) -> list[Path]:
    jars = []
    mods_dir = instance_dir / "mods"

    if not mods_dir.exists():
        fail(f"Mods directory does not exist: {mods_dir}")

    for pattern in DEFAULT_MOD_PATTERNS:
        matches = sorted(mods_dir.glob(pattern))
        if not matches:
            fail(f"No mod jars matched pattern {pattern!r} in {mods_dir}")
        jars.extend(matches)

    return sorted(set(jars))


def find_known_default_mod_jars(mods_dir: Path) -> set[Path]:
    jars = set()
    for pattern in DEFAULT_MOD_PATTERNS:
        jars.update(mods_dir.glob(pattern))

    return {path.resolve() for path in jars}


def default_mod_output(jar_path: Path) -> tuple[str | None, str | None]:
    for pattern, output in DEFAULT_MOD_OUTPUTS.items():
        if fnmatchcase(jar_path.name, pattern):
            source_slug, title = output
            return source_slug, title or output_title(source_slug)

    return None, None


def validate_jar(path: Path) -> Path:
    jar_path = path.expanduser()
    if not jar_path.exists():
        fail(f"Jar does not exist: {jar_path}")
    if not jar_path.is_file():
        fail(f"Jar path is not a file: {jar_path}")
    return jar_path


def normalize_locales(locales: list[str] | None) -> tuple[str, ...]:
    selected = locales or list(DEFAULT_LOCALES)
    normalized = []
    seen = set()
    for locale in selected:
        value = normalize_locale_code(locale)
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    if "en_us" not in seen:
        normalized.insert(0, "en_us")

    return tuple(normalized)


def load_minecraft_asset_translations(
    minecraft_install: Path | None,
    jar_path: Path,
    locales: tuple[str, ...],
) -> dict[str, dict[str, str]]:
    translations_by_locale = {locale: {} for locale in locales}
    if minecraft_install is None:
        return translations_by_locale

    index_path = find_asset_index_path(jar_path, minecraft_install)
    if index_path is None:
        return translations_by_locale

    index = read_json(index_path)
    objects = index.get("objects")
    if not isinstance(objects, dict):
        return translations_by_locale

    for locale in locales:
        entry = objects.get(f"minecraft/lang/{locale}.json")
        if not isinstance(entry, dict):
            continue
        asset_hash = entry.get("hash")
        if not isinstance(asset_hash, str):
            continue
        lang_path = minecraft_install / "assets" / "objects" / asset_hash[:2] / asset_hash
        if not lang_path.exists():
            continue
        translations = read_json(lang_path)
        if isinstance(translations, dict):
            translations_by_locale[locale].update(
                {str(key): str(value) for key, value in translations.items()}
            )

    return translations_by_locale


def merge_translations(
    base: dict[str, dict[str, str]],
    overlay: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    merged = {}
    for locale in sorted(set(base) | set(overlay)):
        merged[locale] = {**base.get(locale, {}), **overlay.get(locale, {})}

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
    translations_by_locale: dict[str, dict[str, str]],
) -> dict[str, Any]:
    identifier = advancement_id(zip_path)
    display = data.get("display")
    display = display if isinstance(display, dict) else {}
    criteria = data.get("criteria")
    criteria = criteria if isinstance(criteria, dict) else {}
    en_us_translations = translations_by_locale.get("en_us", {})
    localized = {}

    for locale, translations in translations_by_locale.items():
        fallback_translations = {**en_us_translations, **translations}
        localized[locale] = {
            "title": format_text(display.get("title"), fallback_translations),
            "description": format_text(
                display.get("description"),
                fallback_translations,
            ),
        }

    title = localized.get("en_us", {}).get("title")
    description = localized.get("en_us", {}).get("description")

    return {
        "id": identifier,
        "namespace": identifier.split(":", 1)[0],
        "path": identifier.split(":", 1)[1],
        "category": category_from_id(identifier),
        "title": title,
        "description": description,
        "localized": localized,
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
    jar_path: Path,
    locales: tuple[str, ...],
    minecraft_install: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = []
    skipped = 0
    locale_set = set(locales)
    translations_from_zip = {locale: {} for locale in locales}
    advancement_files = []

    with ZipFile(jar_path) as zip_file:
        for name in sorted(zip_file.namelist()):
            # Collect translations
            lang_match = LANG_RE.match(name)
            if lang_match:
                locale = normalize_locale_code(lang_match.group("locale"))
                if locale in locale_set:
                    try:
                        with zip_file.open(name) as f:
                            translations = json.load(f)
                            if isinstance(translations, dict):
                                translations_from_zip[locale].update(
                                    {str(key): str(value) for key, value in translations.items()}
                                )
                    except (json.JSONDecodeError, OSError):
                        continue
                continue

            # Collect advancement candidates
            if ADVANCEMENT_RE.match(name):
                advancement_files.append(name)

        translations_by_locale = merge_translations(
            load_minecraft_asset_translations(minecraft_install, jar_path, locales),
            translations_from_zip,
        )

        for name in advancement_files:
            try:
                with zip_file.open(name) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            if not isinstance(data, dict):
                continue

            if not isinstance(data.get("display"), dict):
                skipped += 1
                continue

            records.append(make_record(jar_path, name, data, translations_by_locale))

    meta = {
        "source_archive": str(jar_path),
        "advancement_count": len(records),
        "skipped_without_display_count": skipped,
        "locales": list(locales),
    }
    return records, meta


def has_displayed_advancements(jar_path: Path) -> bool:
    with ZipFile(jar_path) as zip_file:
        for name in zip_file.namelist():
            if not ADVANCEMENT_RE.match(name):
                continue

            try:
                with zip_file.open(name) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            if isinstance(data, dict) and isinstance(data.get("display"), dict):
                return True

    return False


def discover_mod_jars(instance_dir: Path) -> list[Path]:
    mods_dir = instance_dir / "mods"
    if not mods_dir.exists():
        fail(f"Mods directory does not exist: {mods_dir}")

    known_jars = find_known_default_mod_jars(mods_dir)
    discovered = []
    for jar_path in sorted(mods_dir.glob("*.jar"), key=lambda path: path.name.lower()):
        if jar_path.resolve() in known_jars:
            continue
        if has_displayed_advancements(jar_path):
            discovered.append(jar_path)

    return discovered


def output_slug(records: list[dict[str, Any]], fallback: str) -> str:
    namespaces = sorted({record["namespace"] for record in records})
    if len(namespaces) == 1:
        return namespaces[0]

    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", fallback.lower()).strip("_")
    return slug or "unknown"


def output_title(source_slug: str) -> str:
    return OUTPUT_TITLES.get(source_slug, source_slug)


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
    meta: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title} Advancements",
        "",
        f"Source: `{meta['source_archive']}`",
        f"Count: {meta['advancement_count']}",
        f"Skipped without display: {meta['skipped_without_display_count']}",
        f"Locales: `{', '.join(meta['locales'])}`",
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
    source_slug: str,
    title: str,
    records: list[dict[str, Any]],
    meta: dict[str, Any],
) -> list[Path]:
    base_dir = output_dir / source_slug
    payload = {"meta": meta, "advancements": records}
    by_id = {record["id"]: record for record in records}
    counts_by_category: dict[str, int] = {}

    for record in records:
        category = record["category"] or "uncategorized"
        counts_by_category[category] = counts_by_category.get(category, 0) + 1

    index = {
        **meta,
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
    write_markdown(files[3], title, meta, records)
    return files


def output_path_for_print(path: Path) -> Path:
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path


def extract_archive(
    output_dir: Path,
    jar_path: Path,
    source_slug: str | None,
    title: str | None,
    locales: tuple[str, ...],
    minecraft_install: Path | None,
) -> tuple[list[dict[str, Any]], list[Path]]:
    records, meta = collect_advancements(jar_path, locales, minecraft_install)
    resolved_slug = source_slug or output_slug(records, jar_path.stem)
    resolved_title = title or output_title(resolved_slug)
    files = write_outputs(output_dir, resolved_slug, resolved_title, records, meta)
    return records, files


def test_archive(
    jar_path: Path,
    locales: tuple[str, ...],
    minecraft_install: Path | None,
) -> int:
    records, _ = collect_advancements(jar_path, locales, minecraft_install)
    if records:
        print(f"Mod has advancements: {jar_path} ({len(records)} extractable)")
        return 0

    print(f"Mod has no extractable advancements: {jar_path}")
    return 1


def main() -> int:
    args = parse_args()
    if args.discover:
        instance_dir = get_curseforge_instance_dir()
        for jar_path in discover_mod_jars(instance_dir):
            print(jar_path.name)
        return 0

    locales = normalize_locales(args.locales)
    if args.test:
        jar_path = validate_jar(args.jar)
        minecraft_install = find_minecraft_install(jar_path)
        return test_archive(jar_path, locales, minecraft_install)

    if args.jar:
        jar_path = validate_jar(args.jar)
        minecraft_install = find_minecraft_install(jar_path)
        source_slug, title = default_mod_output(jar_path)
        archives: list[tuple[Path, str | None, str | None]] = [
            (jar_path, source_slug, title),
        ]
    else:
        instance_dir = get_curseforge_instance_dir()
        version = get_minecraft_version(instance_dir)
        minecraft_jar = find_minecraft_jar(instance_dir, version)
        minecraft_install = find_minecraft_install(minecraft_jar)
        archives = [(minecraft_jar, "minecraft", "Minecraft")]

        for mod_jar in find_default_mod_jars(instance_dir):
            source_slug, title = default_mod_output(mod_jar)
            archives.append((mod_jar, source_slug, title))

    for jar_path, source_slug, title in archives:
        records, files = extract_archive(
            args.output_dir,
            jar_path,
            source_slug,
            title,
            locales,
            minecraft_install,
        )

        print(f"Extracted {len(records)} advancements from {jar_path}")
        for path in files:
            print(output_path_for_print(path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
