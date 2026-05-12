# Varda Modpack Agent Notes

These notes apply to the whole repository. Varda is a Minecraft modpack centered on Ars Nouveau, magic, exploration, and building. The core design rule is: no RF, FE, or conventional industrial power progression. If a feature needs energy or automation, prefer Ars Nouveau source, magical systems, exploration rewards, or manual/building-focused alternatives.

## Current Pack Direction

- Public pack: <https://www.curseforge.com/minecraft/modpacks/varda>
- Current public target: Minecraft 1.21.1, NeoForge.
- Theme: Ars Nouveau-centered magic, exploration, adventure/RPG, multiplayer, and building.
- Long-term goal: add quests that teach Ars Nouveau/source progression, reward exploration, and gently guide players without turning the pack into a tech pack.
- Avoid adding or enabling mods whose main progression depends on RF/FE, machinery, generators, cables, industrial processing, or tech-style automation.
- If a useful mod contains only a few incompatible RF/FE items, disable those recipes with KubeJS and document why the mod still fits Varda.

## Repository Layout

- `pack-configs/` contains the files copied into a local CurseForge instance.
- `pack-configs/config/` is the main Minecraft `config` directory.
- `pack-configs/defaultconfigs/` is copied into the instance `defaultconfigs` directory. Keep only files that truly need default config loading there.
- `pack-configs/kubejs/` is the main place for recipe edits, disabled recipes, hidden recipe-viewer entries, and future quest-related KubeJS logic.
- `pack-configs/profileImage/` contains pack branding assets.
- `pack-configs/shaderpacks/` and `pack-configs/optionsshaders.txt` are synced when present.
- `configureddefaults` is not used.
- `docs/manifest.json` is the GitHub Pages manifest for the separate server installer repo.
- `docs/MODS.md` tracks important mod dependency notes.
- `scripts/` contains PowerShell and shell helper scripts for local development.
- `PACK_DIR.txt`, `varda-server/`, and `varda-server.zip` are local/generated and intentionally ignored.

## Python Script Reference

- `scripts/prep-files.py` builds the CurseForge client zip, `tmp/release/varda-server-config-<version>.zip`, and `docs/manifest.json`.
- `scripts/cf-upload.py` uploads to CurseForge. Default behavior uploads the client zip. `--client-only`, `--server-only`, `--parent-file-id`, and `--dry-run` are supported.
- `scripts/gh-upload.py` uploads the server config ZIP to GitHub Releases.
- `scripts/reset-sync.py` resets a local CurseForge instance and copies the repo's synced files into it.
- `scripts/copy-confs.py` pulls FTB Quests and Structurify config files back from the configured instance into the repo.
- `scripts/advancements.py` extracts displayed advancement metadata from the vanilla jar and mod jars. `--discover` scans instance mods for jars with displayed advancements that are not already in `DEFAULT_MOD_PATTERNS`.
- `scripts/locate.py` reports structure IDs recorded in the chunk containing the requested block coordinates across all saves in the configured instance.

## Local Workflow

1. Run `.\scripts\set-pack-dir.ps1` once, or create `PACK_DIR.txt` manually with the full path to the local CurseForge instance.
2. Linux/macOS equivalent: `./scripts/set-pack-dir.sh`.
3. Use `.\scripts\reset-sync.ps1` to wipe and copy this repo's configs into the instance.
4. Linux/macOS equivalent: `./scripts/reset-sync.sh`.
5. Use `.\scripts\reset-sync.ps1 -NoPause` when automation needs a non-interactive sync.
6. Use `.\scripts\reset-sync.ps1 -FullWipe` only when a full local instance wipe is intended.

Be careful with sync scripts. They delete files in the configured instance directory. Do not run full wipes unless that is part of the task.
`reset-sync.ps1 -FullWipe` should not delete `resourcepacks` or `shaderpacks`; CurseForge may not restore those automatically. It may delete generated cache folders such as `dynamic-data-pack-cache`, `dynamic-resource-pack-cache`, and `moonlight-global-datapacks`.
Reset sync copies `pack-configs/config`, `pack-configs/defaultconfigs`, `pack-configs/kubejs`, `pack-configs/profileImage`, `pack-configs/shaderpacks`, and `pack-configs/optionsshaders.txt` when present. Files matching the hardcoded `*.disabled` exclude pattern are skipped during directory syncs.

## Mod And Config Policy

- Keep Ars Nouveau and its addons as the center of power, utility, and progression.
- Treat "source-only" as a hard design constraint. Do not introduce RF/FE as an alternate path.
- For recipe removals, prefer small KubeJS scripts under `pack-configs/kubejs/server_scripts/disable/`.
- Use `//requires: modid` on mod-specific KubeJS files so missing optional mods do not break script loading.
- Keep disabled recipe lists explicit and grouped by mod.
- Do not hide unrelated gameplay behind broad recipe removals. Disable the exact item, block, or upgrade that violates the pack direction.
- When hiding recipe-viewer entries, mirror the existing `pack-configs/kubejs/client_scripts/hide/` logging style: log the summary count and each removed entry.
- When disabling server recipes, mirror the existing `pack-configs/kubejs/server_scripts/disable/` logging style unless the script is marked `//ignored: true`.
- When adding mods, check client/server side requirements and update `docs/MODS.md` when dependency relationships matter.
- Watch for configs or scripts that still refer to older Forge/1.20.1 assumptions. The public pack is now 1.21.1 NeoForge, but some server scripts may lag behind.

## Quest Design Notes

Future quests should be implemented as guidance, not a forced checklist. Good quest lines for Varda:

- introduce spell crafting, glyph progression, source generation, rituals, familiars, and magical storage;
- send players to overworld structures, dungeons, ruins, and new dimensions;
- reward exploration with magical materials, building blocks, curios, glyph unlock support, or quality-of-life items;
- explain disabled tech/RF expectations through in-world flavor or concise quest text;
- avoid rewards that skip Ars Nouveau progression or trivialize exploration.

If adding FTB Quests or another quest system, keep quest files in the appropriate exported config path under `pack-configs/`, and update this file with the exact authoring/export workflow once established.

## Verification

There is no conventional unit test suite for this repo. Verify changes with the most relevant practical checks:

- Run `.\scripts\reset-sync.ps1 -NoPause` after config or KubeJS changes when a local instance is configured.
- Launch the CurseForge instance and create/load a test world after recipe/config changes.
- Check `latest.log` for KubeJS script errors.
- Use JEI to confirm disabled RF/FE recipes are gone and intended magical alternatives still exist.

## Editing Guidelines

- Keep changes small and directly tied to the requested pack behavior.
- Preserve user-generated configs, local instance files, and ignored generated outputs.
- Do not commit or depend on `PACK_DIR.txt`, `varda-server/`, `varda-server.zip`, crash reports, logs, saves, or downloaded mod jars unless the repo intentionally changes policy.
- If temporary verification files are needed, create them under the ignored repo-local `.codex-tmp/` scratch directory and clean up task-specific contents when they are no longer useful.
- Keep shell scripts (`*.sh`, `*.bash`, `*.zsh`) LF-only with a final newline. `.gitattributes`, `.editorconfig`, and `.vscode/settings.json` enforce this for Git and editors.
- Keep PowerShell scripts (`*.ps1`) CRLF-only with a final newline. After editing a PowerShell script with automation, verify `git ls-files --eol -- scripts/*.ps1` reports `w/crlf`.
- Prefer ASCII in text files unless editing existing non-ASCII content.
- When uncertain about current mod versions, CurseForge metadata, NeoForge behavior, or KubeJS syntax for the active Minecraft version, verify against current primary sources before changing configs.
