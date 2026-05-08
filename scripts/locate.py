import argparse
import gzip
import struct
import sys
import zlib
from pathlib import Path
from typing import Any

from lib import get_curseforge_instance_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "List structure identifiers in the chunk containing block X/Z "
            "coordinates across every save in CURSEFORGE_INSTANCE_DIR."
        )
    )
    parser.add_argument("x", type=int, help="Block X coordinate.")
    parser.add_argument("z", type=int, help="Block Z coordinate.")
    return parser.parse_args()


def list_save_dirs(instance_dir: Path) -> list[Path]:
    saves_dir = instance_dir / "saves"
    if not saves_dir.exists():
        raise FileNotFoundError(f"Saves directory does not exist: {saves_dir}")

    saves = sorted(path for path in saves_dir.iterdir() if path.is_dir())
    if not saves:
        raise FileNotFoundError(f"No saves found in: {saves_dir}")

    return saves


def get_region_file_for_block(
    save_dir: Path, block_x: int, block_z: int
) -> tuple[Path, int, int, int, int]:
    chunk_x = block_x // 16
    chunk_z = block_z // 16
    region_x = chunk_x // 32
    region_z = chunk_z // 32
    local_x = chunk_x % 32
    local_z = chunk_z % 32
    region_file = save_dir / "region" / f"r.{region_x}.{region_z}.mca"

    return region_file, local_x, local_z, chunk_x, chunk_z


def decompress_payload(payload: bytes, compression: int) -> bytes:
    if compression == 1:
        return gzip.decompress(payload)
    if compression == 2:
        return zlib.decompress(payload)
    if compression == 3:
        return payload

    raise ValueError(f"Unsupported compression type: {compression}")


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


class NbtReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def read(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.data):
            raise ValueError("Unexpected end of NBT data")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def read_byte(self) -> int:
        return self.read(1)[0]

    def read_signed_byte(self) -> int:
        return struct.unpack(">b", self.read(1))[0]

    def read_short(self) -> int:
        return struct.unpack(">h", self.read(2))[0]

    def read_unsigned_short(self) -> int:
        return struct.unpack(">H", self.read(2))[0]

    def read_int(self) -> int:
        return struct.unpack(">i", self.read(4))[0]

    def read_long(self) -> int:
        return struct.unpack(">q", self.read(8))[0]

    def read_float(self) -> float:
        return struct.unpack(">f", self.read(4))[0]

    def read_double(self) -> float:
        return struct.unpack(">d", self.read(8))[0]

    def read_string(self) -> str:
        length = self.read_unsigned_short()
        return self.read(length).decode("utf-8")

    def read_payload(self, tag_type: int) -> Any:
        if tag_type == 1:
            return self.read_signed_byte()
        if tag_type == 2:
            return self.read_short()
        if tag_type == 3:
            return self.read_int()
        if tag_type == 4:
            return self.read_long()
        if tag_type == 5:
            return self.read_float()
        if tag_type == 6:
            return self.read_double()
        if tag_type == 7:
            return self.read(self.read_int())
        if tag_type == 8:
            return self.read_string()
        if tag_type == 9:
            item_type = self.read_byte()
            length = self.read_int()
            return [self.read_payload(item_type) for _ in range(length)]
        if tag_type == 10:
            compound = {}
            while True:
                child_type = self.read_byte()
                if child_type == 0:
                    return compound
                child_name = self.read_string()
                compound[child_name] = self.read_payload(child_type)
        if tag_type == 11:
            return [self.read_int() for _ in range(self.read_int())]
        if tag_type == 12:
            return [self.read_long() for _ in range(self.read_int())]

        raise ValueError(f"Unsupported NBT tag type: {tag_type}")


def read_nbt(raw: bytes) -> dict[str, Any]:
    reader = NbtReader(raw)
    root_type = reader.read_byte()
    if root_type != 10:
        raise ValueError(f"Expected root compound NBT tag, got: {root_type}")

    reader.read_string()
    root = reader.read_payload(root_type)
    if not isinstance(root, dict):
        raise ValueError("Expected root NBT payload to be a compound")

    return root


def find_structures(raw: bytes) -> list[str]:
    root = read_nbt(raw)
    structures = root.get("structures", {})
    if not isinstance(structures, dict):
        return []

    structure_ids = set()
    for key in ("starts", "References"):
        values = structures.get(key, {})
        if isinstance(values, dict):
            structure_ids.update(values)

    return sorted(
        structure_id for structure_id in structure_ids if ":" in structure_id
    )


def validate_region_files(
    save_dirs: list[Path], block_x: int, block_z: int
) -> list[tuple[Path, Path, int, int, int, int]]:
    targets = []
    missing = []

    for save_dir in save_dirs:
        region_file, local_x, local_z, chunk_x, chunk_z = get_region_file_for_block(
            save_dir, block_x, block_z
        )
        if not region_file.exists():
            missing.append(f"{save_dir.name}: {region_file}")
            continue
        targets.append((save_dir, region_file, local_x, local_z, chunk_x, chunk_z))

    if missing:
        raise FileNotFoundError(
            "Missing region file for requested coordinates:\n" + "\n".join(missing)
        )

    return targets


def print_save_structures(save_name: str, structures: list[str]) -> None:
    print(f"{save_name}:")
    if structures:
        for structure in structures:
            print(f"  {structure}")
    else:
        print("  (none)")


def scan_saves(block_x: int, block_z: int) -> int:
    instance_dir = get_curseforge_instance_dir()
    targets = validate_region_files(list_save_dirs(instance_dir), block_x, block_z)

    for index, (save_dir, region_file, local_x, local_z, chunk_x, chunk_z) in enumerate(
        targets
    ):
        raw = read_region_chunk(region_file.read_bytes(), local_x, local_z)
        if raw is None:
            raise ValueError(
                f"No chunk data for {save_dir.name} at chunk {chunk_x},{chunk_z} "
                f"({region_file.name}, local {local_x},{local_z})."
            )

        if index:
            print()
        print_save_structures(save_dir.name, find_structures(raw))

    return 0


def main() -> int:
    args = parse_args()

    try:
        return scan_saves(args.x, args.z)
    except (FileNotFoundError, ValueError, struct.error, zlib.error, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
