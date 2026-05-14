# Varda Modpack

Tools and content for building and publishing the Varda CurseForge client pack, server config ZIP, and GitHub Pages manifest.

## Environment Setup
Create a `.env` file in the repo root:

```ini
CURSEFORGE_INSTANCE_DIR=""
CURSEFORGE_API_TOKEN=""
GITHUB_RELEASES_PAT=""
MODRINTH_API_TOKEN=""
```

These values are read by the tools when needed. They are not injected into your shell environment.

- `CURSEFORGE_INSTANCE_DIR` should point at the local CurseForge instance directory for the pack.
- `CURSEFORGE_API_TOKEN` is used for CurseForge uploads.
- `GITHUB_RELEASES_PAT` is used for GitHub Releases uploads.
- `MODRINTH_API_TOKEN` is used by Modrinth-related tooling.

## Tooling
The automation lives in [`tools/`](tools/). It requires Python. See [pack-docs/PYTHON.md](pack-docs/PYTHON.md) for setup help.

Some tools also depend on [`jsonschema`](https://github.com/python-jsonschema/jsonschema):

```bash
python -m pip install jsonschema
```

Or on Arch Linux:

```bash
sudo pacman -S python-jsonschema
```

All tools support `-h` / `--help`.

### Common Tools
- [`tools/locate.py`](tools/locate.py) locates a structure from chunk coordinates.
- [`tools/advancements.py`](tools/advancements.py) extracts displayed Minecraft and mod advancements.
- [`tools/copy-confs.py`](tools/copy-confs.py) copies FTB Quests and Structurify configuration from the instance into this repo.
- [`tools/reset-sync.py`](tools/reset-sync.py) resets the instance configuration and syncs repository files back into it.
- [`tools/prep-files.py`](tools/prep-files.py) prepares release artifacts.
- [`tools/cf-upload.py`](tools/cf-upload.py) uploads the CurseForge client ZIP.
- [`tools/gh-upload.py`](tools/gh-upload.py) uploads the server config ZIP to GitHub Releases.

## Release Workflow
Typical release flow:

1. Build the release artifacts:

   ```bash
   .\tools\prep-files.py -v 0.1.2 -r beta -q
   ```

2. Upload the CurseForge client ZIP:

   ```bash
   .\tools\cf-upload.py -v 0.1.2 -r beta -c "A meaningful comment."
   ```

3. Upload the server config ZIP to GitHub Releases:

   ```bash
   .\tools\gh-upload.py -v 0.1.2 -c "A meaningful comment."
   ```

4. Push the repo so GitHub Pages picks up the generated [`docs/manifest.json`](docs/manifest.json).

## Repository Layout
- `pack-configs/config` is the main Minecraft `config` directory.
- `pack-configs/defaultconfigs` is copied to the instance/server `defaultconfigs` directory.
- `pack-configs/kubejs` contains KubeJS config plus client and server scripts.
- `pack-configs/profileImage`, `pack-configs/shaderpacks`, and `pack-configs/optionsshaders.txt` are synced into the instance when present.
- `tools/tests/` contains unit tests for the release tooling.
- `docs/` contains the published Pages manifest and related output.

## Notes
- Keep `pack-configs` authoritative for content that should ship in the pack.
- Keep generated release artifacts out of version control.
- If a release looks wrong, check the current CurseForge instance state first; the tooling reads from the live instance data when preparing client manifests.
