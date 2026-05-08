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
LANG_RE = re.compile(r"^assets/[^/]+/lang/(?P<locale>[a-z_]+)\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract displayed advancement metadata from the vanilla Minecraft "
            "jar and default mod jars for the instance configured in PACK_DIR.txt."
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
        help=(
            "Extract only this jar. Defaults to the vanilla Minecraft jar and "
            "default mod jars."
        ),
    )
    parser.add_argument(
        "--locale",
        action="append",
        dest="locales",
        help=(
            "Locale to include in generated metadata. Can be passed multiple "
            "times. Defaults to the pack-supported locales."
        ),
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


def get_minecraft_version(pack_dir: Path) -> str:
    manifest = read_json(find_manifest(pack_dir))
    try:
        version = manifest["minecraft"]["version"]
    except KeyError as error:
        raise KeyError("manifest.json is missing minecraft.version") from error

    if not isinstance(version, str) or not version:
        raise ValueError("manifest.json minecraft.version must be a non-empty string")

    return version


def find_minecraft_jar(pack_dir: Path, version: str) -> Path:
    minecraft_root = find_minecraft_root(pack_dir)
    jar_path = minecraft_root / "Install" / "versions" / version / f"{version}.jar"
    if not jar_path.exists():
        raise FileNotFoundError(f"Minecraft jar does not exist: {jar_path}")

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


def find_default_mod_jars(pack_dir: Path) -> list[Path]:
    jars = []
    mods_dir = pack_dir / "mods"

    if not mods_dir.exists():
        raise FileNotFoundError(f"Mods directory does not exist: {mods_dir}")

    for pattern in DEFAULT_MOD_PATTERNS:
        matches = sorted(mods_dir.glob(pattern))
        if not matches:
            raise FileNotFoundError(
                f"No mod jars matched pattern {pattern!r} in {mods_dir}"
            )
        jars.extend(matches)

    return sorted(set(jars))


def validate_jar(path: Path) -> Path:
    jar_path = path.expanduser()
    if not jar_path.exists():
        raise FileNotFoundError(f"Jar does not exist: {jar_path}")
    if not jar_path.is_file():
        raise FileNotFoundError(f"Jar path is not a file: {jar_path}")
    return jar_path


def read_zip_json(zip_file: ZipFile, name: str) -> Any:
    with zip_file.open(name) as file:
        return json.load(file)


def normalize_locales(locales: list[str] | None) -> tuple[str, ...]:
    selected = locales or list(DEFAULT_LOCALES)
    normalized = []
    seen = set()
    for locale in selected:
        value = locale.strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    if "en_us" not in seen:
        normalized.insert(0, "en_us")

    return tuple(normalized)


def load_zip_translations(
    zip_file: ZipFile,
    locales: tuple[str, ...],
) -> dict[str, dict[str, str]]:
    translations_by_locale = {locale: {} for locale in locales}
    locale_set = set(locales)

    for name in sorted(zip_file.namelist()):
        match = LANG_RE.match(name)
        if not match:
            continue

        locale = match.group("locale")
        if locale not in locale_set:
            continue

        translations = read_zip_json(zip_file, name)
        if isinstance(translations, dict):
            translations_by_locale[locale].update(
                {str(key): str(value) for key, value in translations.items()}
            )

    return translations_by_locale


def asset_object_path(minecraft_install: Path, asset_hash: str) -> Path:
    return minecraft_install / "assets" / "objects" / asset_hash[:2] / asset_hash


def load_minecraft_asset_translations(
    minecraft_install: Path | None,
    jar_path: Path,
    locales: tuple[str, ...],
) -> dict[str, dict[str, str]]:
    if minecraft_install is None:
        return {locale: {} for locale in locales}

    index_path = find_asset_index_path(jar_path, minecraft_install)
    if index_path is None:
        return {locale: {} for locale in locales}

    index = read_json(index_path)
    objects = index.get("objects")
    if not isinstance(objects, dict):
        return {locale: {} for locale in locales}

    translations_by_locale = {locale: {} for locale in locales}
    for locale in locales:
        entry = objects.get(f"minecraft/lang/{locale}.json")
        if not isinstance(entry, dict):
            continue
        asset_hash = entry.get("hash")
        if not isinstance(asset_hash, str):
            continue
        lang_path = asset_object_path(minecraft_install, asset_hash)
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

    with ZipFile(jar_path) as zip_file:
        names = zip_file.namelist()
        translations_by_locale = merge_translations(
            load_minecraft_asset_translations(minecraft_install, jar_path, locales),
            load_zip_translations(zip_file, locales),
        )

        for name in sorted(names):
            if not ADVANCEMENT_RE.match(name):
                continue

            data = read_zip_json(zip_file, name)
            if not isinstance(data, dict):
                raise ValueError(f"Expected advancement JSON object in {name}")

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


def main() -> int:
    args = parse_args()
    locales = normalize_locales(args.locales)
    if args.jar:
        jar_path = validate_jar(args.jar)
        minecraft_install = find_minecraft_install(jar_path)
        archives: list[tuple[Path, str | None, str | None]] = [
            (jar_path, None, None),
        ]
    else:
        pack_dir = read_pack_dir()
        version = get_minecraft_version(pack_dir)
        minecraft_jar = find_minecraft_jar(pack_dir, version)
        minecraft_install = find_minecraft_install(minecraft_jar)
        archives = [(minecraft_jar, "minecraft", "Minecraft")]

        for mod_jar in find_default_mod_jars(pack_dir):
            archives.append((mod_jar, None, None))

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
