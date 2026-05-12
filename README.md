# Varda Modpack

## Environment Setup
Create a .env file in the repo root with:  
```
CURSEFORGE_INSTANCE_DIR=""
CURSEFORGE_API_TOKEN=""
GITHUB_RELEASES_PAT=""
```
These don't actually get injected into the environment, just read by the scripts.  
- Instance directory example: `C:\Users\varda-dev\curseforge\minecraft\Instances\Varda`  
- Curseforge API token can be found/generated at [https://legacy.curseforge.com/account/api-tokens](https://legacy.curseforge.com/account/api-tokens)  
- You'll need repo access to get a `GITHUB_RELEASES_PAT`.

## Scripts
- Scripts require Python. See [pack-docs/PYTHON.md](pack-docs/PYTHON.md) for help.  
- All scripts come with `-h` / `--help`
### `.\scripts\locate.py`
Locate the name of a structure from the X / Z coordinates of the chunk you're in.  
### `.\scripts\advancements.py`
Extract *displayed* advancements for Minecraft and mods.
### `.\scripts\copy-confs.py`
Copies FTB Quests and Structurify configuration files from instance directory into this repo, overwriting what's here.
### `.\scripts\reset-sync.py`
Resets the instance directory's configuration and files and syncs configuration files from this repo.
### `.\scripts\prep-files.py`
Prepares CurseForge client ZIP and server configuration files for GitHub Releases upload.
### `.\scripts\cf-upload.py`
Uploads CurseForge client ZIP.
### `.\scripts\gh-upload.py`
Uploads server configuration files to GitHub releases for the [varda-server-installer](https://github.com/varda-dev/varda-server-installer).

### Release Publishing
- Build release artifacts with `.\scripts\prep-files.py -v 0.1.2 -r beta -q`.
- Upload the CurseForge client zip with `.\scripts\cf-upload.py -v 0.1.2 -r beta -c "A meaningful comment."`.
- Upload the server config ZIP to GitHub Releases with `.\scripts\gh-upload.py -v 0.1.2 -c "A meaningful comment."`.
- Push this repo to update GitHub Pages with what gets generated into `docs\`.

## Config Layout
- `pack-configs/config` is the main Minecraft `config` directory.
- `pack-configs/defaultconfigs` is copied to the instance/server `defaultconfigs` directory. Keep only files that truly need to load as default configs there.
  - Currently nothing uses this directory
- `pack-configs/kubejs` contains the KubeJS config, client scripts, and server scripts.
- `pack-configs/profileImage`, `pack-configs/shaderpacks`, and `pack-configs/optionsshaders.txt` are synced directly into the instance when present.
