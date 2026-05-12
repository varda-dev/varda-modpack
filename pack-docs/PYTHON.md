# Python

## Project Scripts

### `scripts/prep-files.py`
Builds release artifacts in `tmp/release/` and refreshes GitHub Pages manifest files.

- `-v` / `--version` sets the release version
- `-r` / `--release` sets the client zip release channel name, default `beta`
- `-f` / `--force` overwrites existing outputs
- `-q` / `--quiet` prints only errors and final output path(s)
- `--verbose` prints detailed progress

The script writes:

- `tmp/release/varda-client-<version>-<release>.zip`
- `tmp/release/varda-server-config-<version>.zip`
- `docs/manifest.json`
- `docs/index.html`

The server ZIP contains pack files from `pack-configs/` only. No installer binaries or `.varda/*` runtime files are generated here.

### `scripts/cf-upload.py`
Uploads the Varda CurseForge client zip.

- `--dry-run` prints the planned upload metadata without making API calls

### `scripts/gh-upload.py`
Uploads the server config ZIP to GitHub Releases.

- Hardcodes the repository to `varda-dev/varda-modpack`
- `--replace-assets` deletes same-name release assets before reuploading them
- `--dry-run` prints the planned release actions without making API calls

### `scripts/reset-sync.py`
Resets a CurseForge instance and copies the repo's synced pack files into it.

- Default mode performs the minimal wipe and sync
- `--full-wipe` removes additional generated folders and files
- `--inline` copies just KubeJS and FTB Quests without wiping folders first

### `scripts/copy-confs.py`
Copies FTB Quests and Structurify config files from the configured instance back into `pack-configs/config/`.

### `scripts/advancements.py`
Extracts displayed advancement metadata from the vanilla Minecraft jar and mod jars.

- `--discover` scans the instance `mods/` folder for jars with displayed advancements that are not already covered by `DEFAULT_MOD_PATTERNS`
- `--jar` targets a single jar
- `--test` checks whether a single jar has extractable displayed advancements without writing output

### `scripts/locate.py`
Scans all saves in the configured instance and reports structure IDs recorded in the chunk containing the requested block coordinates.

## Windows
### Installation
`winget install --id Python.Launcher -e`  
`winget install --id Python.Python.3.14 -e`  
### Running
To run python scripts directly without requiring e.g. `py script.py`  
Find out where Python's installed - `where.exe py` or `where.exe python`  
From an elevated pwsh prompt, run:  
```
cmd /c assoc .py=Python.File
cmd /c ftype Python.File="C:\Users\<you>\AppData\Local\Programs\Python\Launcher\py.exe" "%L" %*
```
This doesn't need an elevated prompt.  
Now check `$env:PATHEXT`, you may want to adjust the below:   
```
$userPathExt = [Environment]::GetEnvironmentVariable("PATHEXT", "User")

if ([string]::IsNullOrWhiteSpace($userPathExt)) {
  $userPathExt = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL"
}

if ($userPathExt -notmatch '(^|;)\.PY($|;)') {
  [Environment]::SetEnvironmentVariable(
    "PATHEXT",
    "$userPathExt;.PY",
    "User"
  )
}
```
Then close and relaunch pwsh.  

And lastly, associate .py files with Python. Launch "Default apps", search for .py, and select Python for it.  

## Linux
### Installation
```bash
sudo pacman -Syu
sudo pacman -S python python-pip
```
