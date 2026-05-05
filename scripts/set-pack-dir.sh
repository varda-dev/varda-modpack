#!/bin/sh
set -eu

is_blank() {
    [ -z "$(printf '%s' "$1" | tr -d '[:space:]')" ]
}

resolve_existing_path() {
    if [ -d "$1" ]; then
        CDPATH= cd "$1" && pwd -P
        return
    fi

    parent=$(dirname "$1")
    name=$(basename "$1")
    parent=$(CDPATH= cd "$parent" && pwd -P)
    printf '%s/%s\n' "$parent" "$name"
}

absolute_path() {
    case $1 in
        /*) printf '%s\n' "$1" ;;
        *) printf '%s/%s\n' "$(pwd -P)" "$1" ;;
    esac
}

case $0 in
    */*) script_path=$0 ;;
    *) script_path=$(command -v "$0" 2>/dev/null || printf '%s\n' "$0") ;;
esac

script_dir=$(CDPATH= cd "$(dirname "$script_path")" && pwd -P)
repo_root=$(CDPATH= cd "$script_dir/.." && pwd -P)
pack_dir_file=$repo_root/PACK_DIR.txt
pack_dir=${1-}

if is_blank "$pack_dir"; then
    printf 'Enter full path to your modpack instance folder: '
    IFS= read -r pack_dir || pack_dir=
fi

if is_blank "$pack_dir"; then
    printf '%s\n' 'PACK_DIR cannot be empty.' >&2
    exit 1
fi

if [ -e "$pack_dir" ]; then
    pack_dir=$(resolve_existing_path "$pack_dir")
else
    pack_dir=$(absolute_path "$pack_dir")
    printf 'Warning: Path does not exist yet. Writing unresolved path: %s\n' "$pack_dir" >&2
fi

printf '%s\n' "$pack_dir" > "$pack_dir_file"

printf '%s\n' 'PACK_DIR.txt written as:'
cat "$pack_dir_file"
