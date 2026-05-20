# Varda Modpack

Tools and content for building and publishing the Varda CurseForge client pack, server config ZIP, and Blockforge server manifest.

## Environment Setup
Create a `.env` file in the repo root:

```ini
CURSEFORGE_INSTANCE_DIR=""
CURSEFORGE_API_TOKEN=""
MODRINTH_API_TOKEN=""
```

These values are read by the tools when needed. They are not injected into your shell environment.

- `CURSEFORGE_INSTANCE_DIR` should point at the local CurseForge instance directory for the pack.
- `CURSEFORGE_API_TOKEN` is used for CurseForge uploads.
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
- [`tools/varda.py`](tools/varda.py) is the master CLI for reset, prep, copy, and `curseforge` commands.

## Release Workflow
Typical release flow:

1. Build the release artifacts:

   ```bash
   .\tools\varda.py prep -v 0.1.2 -r beta -q
   ```

2. Upload the CurseForge client ZIP:

   ```bash
   .\tools\varda.py curseforge push -v 0.1.2 -r beta -c "A meaningful comment."
   ```

3. Upload the server config ZIP to GitHub Releases:

   ```bash
   gh release create v0.1.2 .\tmp\release\varda-server-config-0.1.2.zip --title "Varda 0.1.2" --notes "A meaningful comment."
   ```

   To replace the ZIP on an existing release:

   ```bash
   gh release upload v0.1.2 .\tmp\release\varda-server-config-0.1.2.zip --clobber
   ```

4. Push the repo so GitHub Pages picks up the generated Blockforge [`docs/manifest.json`](docs/manifest.json).

## Repository Layout
- `pack-configs/config` is the main Minecraft `config` directory.
- `pack-configs/defaultconfigs` is copied to the instance/server `defaultconfigs` directory.
- `pack-configs/kubejs` contains KubeJS config plus client and server scripts.
- `pack-configs/profileImage`, `pack-configs/shaderpacks`, and `pack-configs/optionsshaders.txt` are synced into the instance when present.
- `tools/tests/` contains unit tests for the release tooling.
- `docs/` contains the published Blockforge manifest and related Pages output.

## Notes
- Keep `pack-configs` authoritative for content that should ship in the pack.
- Keep generated release artifacts out of version control.
- If a release looks wrong, check the current CurseForge instance state first; the tooling reads from the live instance data when preparing client manifests.
