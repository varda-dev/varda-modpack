# Varda Modpack
## Tools
- Lettering
  - https://textcraft.net/
  - https://www.minecraftplot.com/minecraft-logo-generator
  - https://www.textstudio.com/logo/minecraft-logo-generator-697
## Scripts
- Run `.\scripts\set-pack-dir.ps1` to configure your modpack directory. It'll create a file that other scripts reference. Or just create `PACK_DIR.txt` in the root of this project with the full path to your modpack directory - e.g. `C:\Users\varda-dev\curseforge\minecraft\Instances\Varda`.
  - Linux/macOS equivalent: `./scripts/set-pack-dir.sh`.
- Run `.\scripts\reset-sync.ps1` to clean up the modpack folder and copy over this repo's changes.
  - Linux/macOS equivalent: `./scripts/reset-sync.sh`.
  - Use `-TargetDirectory` / `-t` to override `PACK_DIR.txt`.
  - Use `-Inline` / `-i` / `--inline` to copy only `pack-configs/kubejs` into the instance without wiping folders, useful before in-game `/kubejs reload`.
  - Use `-FullWipe` / `-f` to delete additional generated instance folders like logs, saves, backups, screenshots, and caches.
  - The sync copies every top-level file and folder in `pack-configs` into the CurseForge instance.
### Config Layout
- `pack-configs/config` is the main Minecraft `config` directory.
- `pack-configs/defaultconfigs` is copied to the instance/server `defaultconfigs` directory. Keep only files that truly need to load as default configs there.
- `pack-configs/kubejs` contains the KubeJS config, client scripts, and server scripts.
- `pack-configs/profileImage`, `pack-configs/shaderpacks`, and `pack-configs/optionsshaders.txt` are synced directly into the instance when present.
## Exporting to CurseForge
- Share Profile -> Export as .zip -> 
  - Everything in config
  - Everything in defaultconfigs
  - Everything in kubejs
  - profileImage
  - shaderpacks
  - optionsshaders.txt
  - Everything in mods
