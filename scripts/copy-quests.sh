#!/bin/sh
set -eu

is_blank() {
  [ -z "$(printf '%s' "$1" | tr -d '[:space:]')" ]
}

trim() {
  printf '%s' "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
}

resolve_directory() {
  CDPATH= cd "$1" && pwd -P
}

case $0 in
  */*) script_path=$0 ;;
  *) script_path=$(command -v "$0" 2>/dev/null || printf '%s\n' "$0") ;;
esac

script_dir=$(CDPATH= cd "$(dirname "$script_path")" && pwd -P)
repo_root=$(CDPATH= cd "$script_dir/.." && pwd -P)
pack_dir_file=$repo_root/PACK_DIR.txt
destination_parent=$repo_root/pack-configs/config
destination=$destination_parent/ftbquests

if [ ! -f "$pack_dir_file" ]; then
  printf '%s\n' 'PACK_DIR.txt not found. Run scripts/set-pack-dir.sh first.' >&2
  exit 1
fi

pack_dir=$(trim "$(cat "$pack_dir_file")")

if is_blank "$pack_dir"; then
  printf '%s\n' 'PACK_DIR cannot be empty.' >&2
  exit 1
fi

if [ ! -d "$pack_dir" ]; then
  printf 'PACK_DIR does not exist: %s\n' "$pack_dir" >&2
  exit 1
fi

pack_dir=$(resolve_directory "$pack_dir")
source=$pack_dir/config/ftbquests

if [ ! -d "$source" ]; then
  printf 'FTB Quests source folder not found: %s\n' "$source" >&2
  exit 1
fi

case $destination in
  ''|/)
    printf 'Refusing to overwrite unsafe destination: %s\n' "$destination" >&2
    exit 1
    ;;
esac

printf '%s\n' '======================================'
printf '%s\n' 'Copy FTB Quests Into Repo'
printf '%s\n' '======================================'
printf 'Source: %s\n' "$source"
printf 'Destination: %s\n' "$destination"
printf '\n'

mkdir -p "$destination_parent"
rm -rf "$destination"
cp -R "$source" "$destination_parent/"

printf '%s\n' 'FTB Quests copied into pack-configs/config.'
