#!/bin/sh
set -eu

usage() {
    cat <<'EOF'
Usage: reset-sync.sh [-t TARGET_DIRECTORY] [-f]

Options:
  -t, --target-directory DIR, -TargetDirectory DIR
      Modpack instance folder. If omitted, PACK_DIR.txt is used.
  -f, --full-wipe, -FullWipe
      Delete additional generated Minecraft instance folders and files.
  -h, --help
      Show this help.
EOF
}

is_blank() {
    [ -z "$(printf '%s' "$1" | tr -d '[:space:]')" ]
}

trim() {
    printf '%s' "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
}

resolve_directory() {
    CDPATH= cd "$1" && pwd -P
}

is_excluded_name() {
    name=$1

    for pattern in $exclude_patterns; do
        case $name in
            $pattern) return 0 ;;
        esac
    done

    return 1
}

copy_directory_filtered() {
    source=$1
    destination=$2

    mkdir -p "$destination"

    (
        CDPATH= cd "$source"

        find . | while IFS= read -r relative_path; do
            [ "$relative_path" = "." ] && continue

            name=${relative_path##*/}
            if is_excluded_name "$name"; then
                continue
            fi

            target_path=$destination/${relative_path#./}

            if [ -d "$relative_path" ]; then
                mkdir -p "$target_path"
                continue
            fi

            target_parent=$(dirname "$target_path")
            mkdir -p "$target_parent"
            cp -f "$relative_path" "$target_path"
        done
    )
}

case $0 in
    */*) script_path=$0 ;;
    *) script_path=$(command -v "$0" 2>/dev/null || printf '%s\n' "$0") ;;
esac

script_dir=$(CDPATH= cd "$(dirname "$script_path")" && pwd -P)
repo_root=$(CDPATH= cd "$script_dir/.." && pwd -P)
pack_dir_file=$repo_root/PACK_DIR.txt
pack_configs_dir=$repo_root/pack-configs
exclude_patterns='*.disabled'

target_directory=
full_wipe=0

while [ "$#" -gt 0 ]; do
    case $1 in
        -t|--target-directory|-TargetDirectory)
            shift
            if [ "$#" -eq 0 ]; then
                printf '%s\n' 'Missing value for target directory.' >&2
                exit 1
            fi
            target_directory=$1
            ;;
        --target-directory=*)
            target_directory=${1#*=}
            ;;
        -f|--full-wipe|-FullWipe)
            full_wipe=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            printf 'Unknown option: %s\n' "$1" >&2
            usage >&2
            exit 1
            ;;
        *)
            if [ -n "$target_directory" ]; then
                printf 'Unexpected argument: %s\n' "$1" >&2
                usage >&2
                exit 1
            fi
            target_directory=$1
            ;;
    esac

    shift
done

if [ "$#" -gt 0 ]; then
    if [ -n "$target_directory" ] || [ "$#" -gt 1 ]; then
        printf '%s\n' 'Unexpected trailing arguments.' >&2
        usage >&2
        exit 1
    fi

    target_directory=$1
fi

if is_blank "$target_directory"; then
    if [ ! -f "$pack_dir_file" ]; then
        printf '%s\n' 'PACK_DIR.txt not found. Run scripts/set-pack-dir.sh first or pass -t.' >&2
        exit 1
    fi

    target_directory=$(trim "$(cat "$pack_dir_file")")
    printf '%s\n' 'Using PACK_DIR from PACK_DIR.txt'
else
    printf '%s\n' 'Using PACK_DIR from target directory parameter'
fi

if is_blank "$target_directory"; then
    printf '%s\n' 'PACK_DIR cannot be empty.' >&2
    exit 1
fi

if [ ! -d "$target_directory" ]; then
    printf 'PACK_DIR does not exist: %s\n' "$target_directory" >&2
    exit 1
fi

pack_dir=$(resolve_directory "$target_directory")

case $pack_dir in
    /)
        printf '%s\n' 'Refusing to use / as PACK_DIR.' >&2
        exit 1
        ;;
esac

if [ "$full_wipe" -eq 1 ]; then
    full_wipe_label=True
else
    full_wipe_label=False
fi

printf '%s\n' '======================================'
printf '%s\n' 'Reset Modpack and Sync Project'
printf '%s\n' '======================================'
printf 'PACK_DIR: %s\n' "$pack_dir"
printf 'FULL_WIPE: %s\n' "$full_wipe_label"
printf '\n'

if [ "$full_wipe" -eq 1 ]; then
    printf '%s\n' 'Performing FULL wipe...'
    folders='.mixin.out .mtsession backups config crash-reports defaultconfigs downloads dynamic-data-pack-cache dynamic-resource-pack-cache ESM ftbbackups3 kubejs local logs moonlight-global-datapacks patchouli_books profileImage saves screenshots'
    files='command_history.txt options.txt patchouli_data.json usercache.json usernamecache.json'
else
    printf '%s\n' 'Performing MINIMAL wipe...'
    folders='config defaultconfigs kubejs'
    files='options.txt'
fi

for folder in $folders; do
    printf 'Deleting folder %s ...\n' "$folder"
    rm -rf "$pack_dir/$folder"
done

for file in $files; do
    printf 'Deleting file %s ...\n' "$file"
    rm -f "$pack_dir/$file"
done

if [ "$full_wipe" -eq 1 ] && [ -d "$pack_dir/shaderpacks" ]; then
    printf '%s\n' 'Deleting shaderpacks/*.txt files ...'
    find "$pack_dir/shaderpacks" -maxdepth 1 -type f -name '*.txt' -exec rm -f {} +
fi

printf '\n'
printf '%s\n' 'Copying configs and assets to instance folder...'

for folder in config defaultconfigs kubejs profileImage; do
    source=$pack_configs_dir/$folder
    destination=$pack_dir/$folder

    if [ ! -d "$source" ]; then
        printf 'Warning: Skipping missing source folder: %s\n' "$source" >&2
        continue
    fi

    printf 'Copying folder %s ...\n' "$folder"
    copy_directory_filtered "$source" "$destination"
done

for folder in shaderpacks; do
    source=$pack_configs_dir/$folder
    destination=$pack_dir/$folder

    if [ ! -d "$source" ]; then
        continue
    fi

    printf 'Copying folder %s ...\n' "$folder"
    copy_directory_filtered "$source" "$destination"
done

printf '\n'
printf '%s\n' 'Modpack reset and synced!'
