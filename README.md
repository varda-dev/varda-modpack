# Varda Modpack

## Environment Setup
Create a .env file in the repo root with:  
```
CURSEFORGE_INSTANCE_DIR=""
CURSEFORGE_API_TOKEN=""
```
- Instance directory example: `C:\Users\varda-dev\curseforge\minecraft\Instances\Varda`  
- Curseforge API token can be found/generated at [https://legacy.curseforge.com/account/api-tokens](https://legacy.curseforge.com/account/api-tokens)  

These don't actually get injected into the environment, just read by the scripts.  

## Scripts
Change to `/` slashes if on Linux.  

Scripts require Python. See [docs/PYTHON.md](docs/PYTHON.md) for help.  

### During Developemtn
- Run `.\scripts\reset-sync.py` to clean up the modpack folder and copy over this repo's changes.
  - Use `.\scripts\reset-sync.py -h` for help.
- Run `.\scripts\locate.py X Z` to inspect the save chunk containing those block coordinates across every save in the instance from `CURSEFORGE_INSTANCE_DIR`.
  - `X` and `Z` are block coordinates, not chunk coordinates. The script converts them to the matching chunk and region file.
  - It reads each save's `.mca` region data directly and reports structure IDs recorded in the chunk's `structures.starts` and `structures.References` NBT.
  - Results are actual structure data for that chunk, not broad text matches from unrelated chunk data like block entities, attachments, or mod state.
  - `(none)` means that save has chunk data at those coordinates, but no structure IDs are recorded for that chunk.

### Uploading to Curseforge
- Run `/scripts/prep-files.py -c -v 0.1.2 -r beta`
- Then upload it `./scripts/cf-upload.py -v 0.1.2 -r beta -c "A meaningful comment."`

Still need to work on server files.  

## Config Layout
- `pack-configs/config` is the main Minecraft `config` directory.
- `pack-configs/defaultconfigs` is copied to the instance/server `defaultconfigs` directory. Keep only files that truly need to load as default configs there.
  - Currently nothing uses this directory
- `pack-configs/kubejs` contains the KubeJS config, client scripts, and server scripts.
- `pack-configs/profileImage`, `pack-configs/shaderpacks`, and `pack-configs/optionsshaders.txt` are synced directly into the instance when present.

## Exporting to CurseForge
I eventually want to automate this with the Curseforge API with `.\scripts\cf-upload.py`  

- Share Profile -> Export as .zip -> 
  - Everything in config
  - From kubejs, client_scripts, config, data, and server_scripts
  - profileImage
  - shaderpacks
  - Everything in mods
