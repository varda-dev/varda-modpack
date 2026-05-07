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
printf '%s\n' '======================================'
printf '%s\n' 'Copy Configs Into Repo'
printf '%s\n' '======================================'

mkdir -p "$destination_parent"

copy_config() {
  name=$1
  relative_path=$2
  path_type=$3
  source=$pack_dir/config/$relative_path
  destination=$destination_parent/$relative_path

  if [ "$path_type" = directory ]; then
    if [ ! -d "$source" ]; then
      printf '%s source not found: %s\n' "$name" "$source" >&2
      exit 1
    fi
  elif [ ! -f "$source" ]; then
    printf '%s source not found: %s\n' "$name" "$source" >&2
    exit 1
  fi

  case $destination in
    ''|/)
      printf 'Refusing to overwrite unsafe destination: %s\n' "$destination" >&2
      exit 1
      ;;
  esac

  printf '%s:\n' "$name"
  printf '  Source: %s\n' "$source"
  printf '  Destination: %s\n' "$destination"

  if [ "$path_type" = directory ]; then
    rm -rf "$destination"
    cp -R "$source" "$destination_parent/"
  else
    mkdir -p "$(dirname "$destination")"
    cp "$source" "$destination"
  fi

  printf '\n'
}

copy_config 'FTB Quests' 'ftbquests' directory
copy_config 'Structurify' 'structurify.json' file

printf '%s\n' 'Configs copied into pack-configs/config.'
