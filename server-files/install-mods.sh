#!/bin/sh
set -eu

MODS_FILE="varda-mods.txt"
MODS_DIR="mods"
STATE_FILE="$MODS_DIR/.varda-mods-installed.txt"

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl is required to install Varda server mods." >&2
  exit 1
fi

if [ ! -f "$MODS_FILE" ]; then
  echo "error: missing $MODS_FILE" >&2
  exit 1
fi

mkdir -p "$MODS_DIR"

tmp_root=$(mktemp -d "${TMPDIR:-/tmp}/varda-mods.XXXXXX")
trap 'rm -rf "$tmp_root"' EXIT HUP INT TERM

desired_state="$tmp_root/desired-state.txt"
old_state="$tmp_root/old-state.txt"
: > "$desired_state"

if [ -f "$STATE_FILE" ]; then
  cp "$STATE_FILE" "$old_state"
fi

validate_file() {
  file_path=$1
  expected_size=$2
  expected_sha1=$3

  if [ ! -f "$file_path" ]; then
    return 1
  fi

  if [ -n "$expected_size" ]; then
    actual_size=$(wc -c < "$file_path" | tr -d '[:space:]')
    if [ "$actual_size" != "$expected_size" ]; then
      return 1
    fi
  fi

  if [ -n "$expected_sha1" ] && command -v sha1sum >/dev/null 2>&1; then
    actual_sha1=$(sha1sum "$file_path" | awk '{print tolower($1)}')
    expected_sha1=$(printf '%s' "$expected_sha1" | tr '[:upper:]' '[:lower:]')
    if [ "$actual_sha1" != "$expected_sha1" ]; then
      return 1
    fi
  fi

  return 0
}

append_state_line() {
  printf '%s|%s|%s|%s\n' "$1" "$2" "$3" "$4" >> "$desired_state"
}

download_file() {
  url=$1
  target=$2
  curl -fL --retry 3 --retry-delay 5 -o "$target" "$url"
}

process_entry() {
  project_id=$1
  file_id=$2
  required=$3
  filename=$4
  size=$5
  sha1=$6
  url=$7

  if [ "$required" != "true" ]; then
    return 0
  fi

  if [ -z "$filename" ] || [ -z "$url" ]; then
    echo "error: invalid varda-mods.txt entry for project $project_id file $file_id" >&2
    exit 1
  fi

  output="$MODS_DIR/$filename"

  if [ -f "$output" ] && validate_file "$output" "$size" "$sha1"; then
    echo "Already valid: $filename"
    append_state_line "$project_id" "$file_id" "$filename" "$sha1"
    return 0
  fi

  temp_file=$(mktemp "$MODS_DIR/.varda-mod.XXXXXX")
  if ! download_file "$url" "$temp_file"; then
    rm -f "$temp_file"
    echo "error: download failed for $filename" >&2
    exit 1
  fi

  if ! validate_file "$temp_file" "$size" "$sha1"; then
    rm -f "$temp_file"
    echo "error: validation failed for $filename" >&2
    exit 1
  fi

  mv -f "$temp_file" "$output"
  echo "Installed: $filename"
  append_state_line "$project_id" "$file_id" "$filename" "$sha1"
}

while IFS='|' read -r project_id file_id required filename size sha1 url; do
  case "$project_id" in
    ""|\#*) continue ;;
  esac
  process_entry "$project_id" "$file_id" "$required" "$filename" "$size" "$sha1" "$url"
done < "$MODS_FILE"

mv -f "$desired_state" "$STATE_FILE"

if [ -f "$old_state" ]; then
  while IFS='|' read -r project_id file_id filename sha1; do
    case "$project_id" in
      ""|\#*) continue ;;
    esac

    if awk -F'|' -v pid="$project_id" -v fname="$filename" '$1 == pid && $3 == fname {found = 1; exit} END {exit(found ? 0 : 1)}' "$STATE_FILE"; then
      continue
    fi

    if [ -n "$filename" ] && [ -f "$MODS_DIR/$filename" ]; then
      rm -f "$MODS_DIR/$filename"
    fi
  done < "$old_state"
fi

echo "Done."
