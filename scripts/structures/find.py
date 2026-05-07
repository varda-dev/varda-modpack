import argparse
import gzip
import re
import struct
import sys
import zlib
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TMP_DIR = SCRIPT_DIR / "tmp"

IDENTIFIER_RE = re.compile(r"[a-z0-9_.-]+:[a-z0-9_/.-]+")
REGION_FILE_RE = re.compile(r"^r\.(-?\d+)\.(-?\d+)\.mca$")

KEYWORDS = [
    "structure",
    "tower",
    "ruin",
    "fortress",
    "temple",
    "village",
    "dungeon",
    "cataclysm",
    "structory",
    "wizard",
    "mvs",
    "mss",
    "philips",
    "formations",
    "ars",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List likely structure identifiers in a chunk file under scripts/structures/tmp/."
    )
    parser.add_argument(
        "chunk_file",
        help="Chunk or region filename. Bare names are resolved relative to scripts/structures/tmp/.",
    )
    parser.add_argument(
        "--chunk-x",
        type=int,
        help="Global chunk X coordinate when reading one chunk from a .mca region file.",
    )
    parser.add_argument(
        "--chunk-z",
        type=int,
        help="Global chunk Z coordinate when reading one chunk from a .mca region file.",
    )
    parser.add_argument(
        "--local-x",
        type=int,
        choices=range(32),
        metavar="0-31",
        help="Local region chunk X coordinate when reading one chunk from a .mca region file.",
    )
    parser.add_argument(
        "--local-z",
        type=int,
        choices=range(32),
        metavar="0-31",
        help="Local region chunk Z coordinate when reading one chunk from a .mca region file.",
    )
    return parser.parse_args()


def resolve_input_file(filename: str) -> Path:
    path = Path(filename)
    if path.exists():
        return path

    tmp_path = TMP_DIR / filename
    if tmp_path.exists():
        return tmp_path

    raise FileNotFoundError(f"Chunk file not found: {filename} or {tmp_path}")


def decompress_payload(payload: bytes, compression: int | None = None) -> bytes:
    if compression == 1:
        return gzip.decompress(payload)
    if compression == 2:
        return zlib.decompress(payload)
    if compression == 3:
        return payload
    if compression is not None:
        raise ValueError(f"Unsupported compression type: {compression}")

    for decompressor in (gzip.decompress, zlib.decompress):
        try:
            return decompressor(payload)
        except OSError:
            pass
        except zlib.error:
            pass

    return payload


def find_structures(raw: bytes) -> list[str]:
    text = raw.decode("latin1", errors="ignore")
    matches = set(IDENTIFIER_RE.findall(text))
    return sorted(
        match for match in matches if any(keyword in match for keyword in KEYWORDS)
    )


def get_region_coords(region_file: Path) -> tuple[int, int] | None:
    match = REGION_FILE_RE.match(region_file.name)
    if not match:
        return None

    return int(match.group(1)), int(match.group(2))


def get_requested_local_coords(args: argparse.Namespace) -> tuple[int, int] | None:
    has_global = args.chunk_x is not None or args.chunk_z is not None
    has_local = args.local_x is not None or args.local_z is not None

    if has_global and has_local:
        raise ValueError("Use either --chunk-x/--chunk-z or --local-x/--local-z, not both.")
    if has_global and (args.chunk_x is None or args.chunk_z is None):
        raise ValueError("--chunk-x and --chunk-z must be provided together.")
    if has_local and (args.local_x is None or args.local_z is None):
        raise ValueError("--local-x and --local-z must be provided together.")

    if has_global:
        return args.chunk_x % 32, args.chunk_z % 32
    if has_local:
        return args.local_x, args.local_z

    return None


def read_region_chunk(region_data: bytes, local_x: int, local_z: int) -> bytes | None:
    index = local_x + local_z * 32
    offset_entry = region_data[index * 4:index * 4 + 4]
    offset = int.from_bytes(offset_entry[:3], "big")

    if offset == 0:
        return None

    chunk_start = offset * 4096
    length = struct.unpack(">I", region_data[chunk_start:chunk_start + 4])[0]
    compression = region_data[chunk_start + 4]
    payload = region_data[chunk_start + 5:chunk_start + 4 + length]
    return decompress_payload(payload, compression)


def print_structures(structures: list[str]) -> None:
    for structure in structures:
        print(structure)


def scan_one_region_chunk(region_file: Path, local_x: int, local_z: int) -> int:
    raw = read_region_chunk(region_file.read_bytes(), local_x, local_z)
    if raw is None:
        print(f"No chunk data at local chunk {local_x},{local_z}.", file=sys.stderr)
        return 1

    print_structures(find_structures(raw))
    return 0


def scan_region(region_file: Path) -> int:
    data = region_file.read_bytes()
    region_coords = get_region_coords(region_file)
    found_any = False

    for local_z in range(32):
        for local_x in range(32):
            raw = read_region_chunk(data, local_x, local_z)
            if raw is None:
                continue

            structures = find_structures(raw)
            if not structures:
                continue

            found_any = True
            if region_coords is None:
                print(f"local chunk {local_x},{local_z}:")
            else:
                chunk_x = region_coords[0] * 32 + local_x
                chunk_z = region_coords[1] * 32 + local_z
                print(f"chunk {chunk_x},{chunk_z} (local {local_x},{local_z}):")
            print_structures(structures)
            print()

    return 0 if found_any else 1


def main() -> int:
    args = parse_args()

    try:
        chunk_file = resolve_input_file(args.chunk_file)
        local_coords = get_requested_local_coords(args)

        if chunk_file.suffix == ".mca":
            if local_coords is not None:
                return scan_one_region_chunk(chunk_file, *local_coords)
            return scan_region(chunk_file)

        print_structures(find_structures(decompress_payload(chunk_file.read_bytes())))
        return 0
    except (FileNotFoundError, ValueError, struct.error) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
