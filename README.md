# Varda Modpack

## Environment Setup
Create a .env file in the repo root with:  
```
CURSEFORGE_INSTANCE_DIR=""
CURSEFORGE_API_TOKEN=""
GITHUB_RELEASES_PAT=""
```
- Instance directory example: `C:\Users\varda-dev\curseforge\minecraft\Instances\Varda`  
- Curseforge API token can be found/generated at [https://legacy.curseforge.com/account/api-tokens](https://legacy.curseforge.com/account/api-tokens)  
- `scripts/gh-upload.py` hardcodes the GitHub repository to `varda-dev/varda-modpack`.

These don't actually get injected into the environment, just read by the scripts.  

## Scripts
Scripts require Python. See [docs/PYTHON.md](docs/PYTHON.md) for help.  

Change to `/` slashes if on Linux.  
### During Development
- All scripts come with `-h` / `--help`
- Run `.\scripts\reset-sync.py` to clean up the modpack folder and copy over this repo's changes.
- Run `.\scripts\locate.py X Z` to inspect the save chunk containing those block coordinates across every save in the instance from `CURSEFORGE_INSTANCE_DIR`.
  - `X` and `Z` are block coordinates, not chunk coordinates. The script converts them to the matching chunk and region file.
  - It reads each save's `.mca` region data directly and reports structure IDs recorded in the chunk's `structures.starts` and `structures.References` NBT.
  - Results are actual structure data for that chunk, not broad text matches from unrelated chunk data like block entities, attachments, or mod state.
  - `(none)` means that save has chunk data at those coordinates, but no structure IDs are recorded for that chunk.

### Release Publishing
- Build release artifacts with `.\scripts\prep-files.py --b -v 0.1.2 -r beta`
  - Add `-q` / `--quiet` to suppress output.
- Upload the CurseForge client zip with `.\scripts\cf-upload.py -v 0.1.2 -r beta -c "A meaningful comment."`
- Upload the server installer binaries to GitHub Releases with `.\scripts\gh-upload.py -v 0.1.2 -r beta -c "A meaningful comment." --replace-assets`
- Release artifacts land in `tmp/release/`. CurseForge gets the client zip only. GitHub Releases gets the server installer binaries and `checksums.txt`.
- See [docs/release.md](docs/release.md) for the split release flow and token setup.

## Config Layout
- `pack-configs/config` is the main Minecraft `config` directory.
- `pack-configs/defaultconfigs` is copied to the instance/server `defaultconfigs` directory. Keep only files that truly need to load as default configs there.
  - Currently nothing uses this directory
- `pack-configs/kubejs` contains the KubeJS config, client scripts, and server scripts.
- `pack-configs/profileImage`, `pack-configs/shaderpacks`, and `pack-configs/optionsshaders.txt` are synced directly into the instance when present.
