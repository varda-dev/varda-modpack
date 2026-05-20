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
- `docs/manifest.json` is the Blockforge server manifest for the separate server installer repo.
- `docs/index.html` is a manually maintained static landing page. `tools/varda.py prep` must not generate it.
- `docs/MODS.md` tracks important mod dependency notes.
- `scripts/` contains PowerShell and shell helper scripts for local development.
- `.codex/skills/ftb-quests/SKILL.md` is the repo-local reusable skill template for Varda quest work.
- `PACK_DIR.txt`, `varda-server/`, and `varda-server.zip` are local/generated and intentionally ignored.
- `tmp/release/` is generated release output. It may contain the CurseForge client zip, `varda-server-config-<version>.zip`, and related build artifacts.
- `pack-docs/` is human-facing markdown only. Do not treat it as agent source of truth for workflow or policy.

## Python Tool Reference

- `tools/varda.py prep` builds the CurseForge client zip, `tmp/release/varda-server-config-<version>.zip`, and Blockforge `docs/manifest.json`.
- `tools/varda.py prep` always overwrites `docs/manifest.json`, but only overwrites release artifacts in `tmp/release/` when `-f/--force` is given.
- `tools/varda.py curseforge push` uploads the client zip to CurseForge. `--parent-file-id` and `--dry-run` are supported.
- Use the GitHub CLI to upload `tmp/release/varda-server-config-<version>.zip` to GitHub Releases.
- `tools/varda.py reset` resets a local CurseForge instance and copies the repo's synced files into it.
- `tools/varda.py copy` pulls FTB Quests and Structurify config files back from the configured instance into the repo.
- `tools/advancements.py` extracts displayed advancement metadata from the vanilla jar and mod jars. `--discover` scans instance mods for jars with displayed advancements that are not already in `DEFAULT_MOD_PATTERNS`.
- `tools/locate.py` reports structure IDs recorded in the chunk containing the requested block coordinates across all saves in the configured instance.

## Quest Authoring

Quest guidance and FTB Quests workflow live here, not in `pack-docs/`. Use `.codex/skills/ftb-quests/SKILL.md` as the reusable workflow template when quest work is requested.

### Current FTB Quests Source Files

- `pack-configs/config/ftbquests/quests/data.snbt` holds global FTB Quests settings.
- `pack-configs/config/ftbquests/quests/chapter_groups.snbt` holds chapter grouping data.
- `pack-configs/config/ftbquests/quests/chapters/*.snbt` holds chapter layout, quests, tasks, rewards, dependencies, and icons.
- `pack-configs/config/ftbquests/quests/lang/en_us.snbt` holds player-facing chapter, quest, and description text.
- `pack-configs/config/ftbquests/quests/lang/es_es.snbt`, `fr_fr.snbt`, and `de_de.snbt` must stay aligned with English keys and ordering where practical.
- Preserve lore and pack proper nouns such as `Varda`, but localize surrounding title words naturally.
- `pack-configs/kubejs/client_scripts/` is available only for client-side presentation or recipe-viewer hiding.

### Quest Intent

- `The Tattered Path` should be first named FTB Quests chapter group in `The Varda Codex`.
- `The Familiar Trail` is vanilla advancement chapter and should appear above `The Hidden Thread`.
- `The Hidden Thread` is intro chapter and currently starts with mobile crafting.
- Quests should guide Ars Nouveau-centered magic, exploration, adventure/RPG, multiplayer, and building.
- Ars Nouveau is main progression identity. Vanilla advancement tabs should support onboarding and milestones, while Ars Nouveau chapters remain core path.
- Do not turn quest book into forced checklist. Use it to teach systems, suggest goals, and reward natural progression.
- Keep pack's no-RF/no-FE direction intact. Rewards and quest goals should reinforce magic, source, exploration, building, or quality-of-life play.
- Keep quest text concise and actionable. Light lore flavor okay.
- Avoid rewards that skip core Ars Nouveau progression, trivialize boss fights, or remove value of exploration.
- For vanilla Minecraft advancement quests, mirror vanilla advancement structure and use modest rewards that echo completed milestone.

### FTB Quests Responsibilities

- Use FTB Quests for visible quest-book layer: chapter groups, chapters, layout, titles, descriptions, icons, item tasks, item rewards, dependencies, and simple linear or branching progression.
- Prefer localized strings in `lang/en_us.snbt` instead of embedding display text directly in chapter files.
- For Minecraft advancement tabs, use native FTB Quests advancement tasks with `type: "advancement"`, `advancement: "minecraft:path/id"`, and empty `criterion` unless a specific criterion is needed.

### KubeJS Bridge

- Use KubeJS for dynamic behavior that is awkward or brittle in FTB Quests alone: boss kill detection, dimension entry detection, structure/biome/location milestones, custom progression flags, mod-specific events, delayed or conditional rewards, and bridge logic for custom quest completion.
- When adding mod-specific KubeJS files, include `//requires: modid` at top so missing optional mods do not break script loading.
- Prefer one of these bridge patterns when a quest needs dynamic completion:
  - KubeJS grants custom advancement, FTB Quests tracks that advancement.
  - KubeJS gives or removes hidden marker item, FTB Quests tracks that item.
  - KubeJS runs FTB Quests progress command, if verified in active pack version.
  - KubeJS stores persistent player or team data and handles reward directly, while FTB Quests provides visible guidance.
- Do not assume advanced FTB task SNBT schemas. If a task type has no known-good local example, verify schema first by exporting a small in-game example or checking current documentation.

### IDs And Files

- Use uppercase 16-character hexadecimal IDs for new FTB chapter, quest, task, and reward IDs, matching existing exported style.
- Keep every generated ID unique across quest files.
- Keep chapter filenames lowercase with underscores.
- Keep quest shapes consistent with current pack default unless user requests different visual style.
- Preserve existing quest IDs unless intentionally migrating or replacing a quest.
- When adding or editing quest, update relevant chapter file and `lang/en_us.snbt`.
- Keep `lang/es_es.snbt`, `lang/fr_fr.snbt`, and `lang/de_de.snbt` on par with English: same keys, same ordering where practical, translated display values.

### Layout

- Keep chapter layouts readable on FTB Quests grid.
- Prefer compact trees or hub-and-spoke clusters over long parallel columns.
- Keep high-fanout dependency quests close to dependents so dependency lines stay short and readable.
- Use simple left-to-right or top-to-bottom progression only when it does not create long diagonal clutter.
- Use dependencies to make progression understandable, but avoid locking unrelated player freedom.
- Give important chapter starts a clear icon and make early quests easy to understand at a glance.

### Verification

- Check SNBT syntax visually for balanced braces, brackets, and commas.
- Search for duplicate generated FTB IDs.
- Confirm every new quest title and description key exists in `lang/en_us.snbt`.
- Confirm every English quest title and description key also exists in `lang/es_es.snbt`, `lang/fr_fr.snbt`, and `lang/de_de.snbt`.
- If KubeJS changed, launch or sync into test instance when practical and check `latest.log` for KubeJS errors.
- For dynamic trigger bridges, test one representative quest end-to-end before expanding pattern broadly.

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
`tools/varda.py prep` is the main local release prep command. It reads `CURSEFORGE_INSTANCE_DIR`, generates the client zip, generates the server config ZIP, and writes Blockforge `docs/manifest.json` for Pages.

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
- Do not make `tools/varda.py prep` generate or overwrite `docs/index.html`; keep that file static unless a human-authored update is intended.
