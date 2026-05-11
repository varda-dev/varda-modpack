# Varda Modpack

Varda is a NeoForge-based Minecraft modpack focused on exploration, combat, and immersive progression. It utilizes KubeJS for game logic modifications and FTB Quests for structured progression.

## Technology Stack
- **Minecraft Version:** 1.21.1
- **Mod Loader:** NeoForge
- **Scripting:** KubeJS (JavaScript)
- **Questing:** FTB Quests
- **Automation:** Python 3 (Scripts for syncing, building, and uploading)

## Project Structure
- `pack-configs/`: Source of truth for modpack configurations.
    - `config/`: Minecraft and mod configuration files.
    - `kubejs/`: Custom scripts for server-side logic (`server_scripts`), client-side tweaks (`client_scripts`), and data modifications (`data`).
    - `profileImage/`: Modpack icon.
- `scripts/`: Python utility scripts for development automation.
- `docs/`: Technical documentation and development guides.
- `server-files/`: Templates and scripts for setting up a dedicated server.

## Environment Setup
Create a `.env` file in the repository root:
```env
CURSEFORGE_INSTANCE_DIR="/path/to/your/curseforge/instance/Varda"
CURSEFORGE_API_TOKEN="your_curseforge_api_token"
```
*Note: Java 21 is required for building server files and running the modpack.*

## Development Workflow

### 1. Syncing to Minecraft Instance
To apply repository changes to your local CurseForge instance:
```bash
python scripts/reset-sync.py
```
- Use `-f` for a full wipe (clears saves, logs, etc.).
- Use `-i` for an "inline" update (copies only scripts/quests without wiping).

### 2. Modifying Quests
FTB Quests should be edited **in-game**. Once finished, sync the changes back to the repository:
```bash
python scripts/copy-confs.py
```
This script pulls `ftbquests` and `structurify.json` from your instance into `pack-configs/config/`.

### 3. Modifying Game Logic (KubeJS)
Edit scripts in `pack-configs/kubejs/server_scripts/`. After editing, you can use `/kubejs reload server` in-game to apply changes without restarting.

### 4. Building Releases
To generate client and server distribution zips:
```bash
python scripts/prep-files.py --both -v 0.1.0 -r beta
```
Output zips are placed in the `tmp/` directory.

### 5. Uploading to CurseForge
```bash
python scripts/cf-upload.py -v 0.1.0 -r beta -c "Changelog message"
```

## Utility Scripts
- `scripts/locate.py X Z`: Inspects world save data to find structure IDs at specific block coordinates.
- `scripts/advancements.py`: Tools for managing or generating advancements.

## Development Guidelines
- **Surgical Updates:** When modifying `kubejs` scripts, maintain existing patterns and logging conventions.
- **Quest Authoring:** Always run `copy-confs.py` immediately after significant in-game quest edits to avoid losing work.
- **Mod Updates:** When adding/removing mods in the CurseForge instance, ensure the `manifest.json` is updated by the CurseForge app, then run `prep-files.py` to verify the build.
