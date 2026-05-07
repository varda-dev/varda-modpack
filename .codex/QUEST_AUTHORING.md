# FTB Quests Authoring Rules

These rules apply when creating or editing Varda quest content. The quest chain lives under `pack-configs/config/ftbquests/quests`, and KubeJS may be used alongside FTB Quests for dynamic progression triggers. The quest book is `The Varda Codex`.

## Source Files

- `pack-configs/config/ftbquests/quests/data.snbt` holds global FTB Quests settings.
- `pack-configs/config/ftbquests/quests/chapter_groups.snbt` holds chapter grouping data.
- `pack-configs/config/ftbquests/quests/chapters/*.snbt` holds chapter layout, quests, tasks, rewards, dependencies, and icons.
- `pack-configs/config/ftbquests/quests/lang/en_us.snbt` holds player-facing chapter, quest, and description text.
- `pack-configs/config/ftbquests/quests/lang/es_es.snbt` holds Spanish player-facing text and must stay aligned with English.
- `pack-configs/config/ftbquests/quests/lang/fr_fr.snbt` holds French player-facing text and must stay aligned with English.
- `pack-configs/config/ftbquests/quests/lang/de_de.snbt` holds German player-facing text and must stay aligned with English.
- Preserve lore and pack proper nouns such as `Varda`, but localize surrounding title words naturally, for example `The Varda Codex` becomes `El Códice de Varda`, `Le Codex de Varda`, or `Der Kodex von Varda`.
- `pack-configs/kubejs/server_scripts/` is available for quest-related server logic.
- `pack-configs/kubejs/client_scripts/` is available only for client-side presentation or recipe-viewer hiding.

## Design Intent

- `The Tattered Path` should be the first named FTB Quests chapter group in `The Varda Codex`.
- `The Familiar Trail` is the vanilla Minecraft advancement chapter and should appear above `The Hidden Thread`.
- `The Hidden Thread` is the introductory chapter that currently starts with mobile crafting.
- Quests should guide players through Varda's Ars Nouveau-centered magic, exploration, adventure, RPG, multiplayer, and building focus.
- Ars Nouveau is the main progression identity. Vanilla Minecraft quest tabs should support onboarding and milestones, while Ars Nouveau chapters should remain the pack's core path.
- Do not turn the quest book into a forced checklist. Use it to teach systems, suggest goals, and reward natural progression.
- Keep the pack's no-RF/no-FE direction intact. Rewards and quest goals should reinforce magic, source, exploration, building, or quality-of-life play.
- Quest text may be lightly lore-flavored, but keep it concise and actionable.
- Avoid rewards that skip core Ars Nouveau progression, trivialize boss fights, or remove the value of exploration.
- For vanilla Minecraft advancement quests, mirror the vanilla advancement structure and use modest rewards that echo the completed milestone.

## FTB Quests Responsibilities

Use FTB Quests for the visible quest-book layer:

- chapter groups, including `The Tattered Path`;
- chapters and chapter ordering;
- quest layout coordinates;
- quest titles and descriptions;
- quest icons;
- item collection or item possession tasks;
- item rewards;
- quest dependencies;
- simple linear or branching progression.

Prefer localized strings in `lang/en_us.snbt` instead of embedding display text directly in chapter files.

For Minecraft advancement tabs, use native FTB Quests advancement tasks with `type: "advancement"`, `advancement: "minecraft:path/id"`, and an empty `criterion` unless a specific criterion is intentionally needed.

## KubeJS Responsibilities

Use KubeJS for dynamic behavior that is awkward or brittle in FTB Quests alone:

- boss kill detection;
- dimension entry detection;
- structure, biome, or location milestones;
- custom progression flags;
- mod-specific events;
- delayed or conditional rewards;
- bridge logic for custom quest completion.

When adding mod-specific KubeJS files, include `//requires: modid` at the top so missing optional mods do not break script loading.

## FTB Quests And KubeJS Bridge

Prefer one of these bridge patterns when a quest needs dynamic completion:

1. KubeJS grants a custom advancement, and FTB Quests tracks that advancement.
2. KubeJS gives or removes a hidden marker item, and FTB Quests tracks that item.
3. KubeJS runs an FTB Quests progress command, if verified in the active pack version.
4. KubeJS stores persistent player or team data and handles the reward directly, while FTB Quests provides the visible guidance.

Do not assume advanced FTB task SNBT schemas. If a task type has no known-good local example, verify the schema first by exporting a small in-game example or checking current documentation.

## ID And File Conventions

- Use uppercase 16-character hexadecimal IDs for new FTB chapter, quest, task, and reward IDs, matching the existing exported style.
- Keep every generated ID unique across the quest files.
- Keep chapter filenames lowercase with underscores.
- Keep quest shapes consistent with the current pack default unless the user requests a different visual style.
- Preserve existing quest IDs unless intentionally migrating or replacing a quest.
- When adding or editing a quest, update both the relevant chapter file and `lang/en_us.snbt`.
- Keep `lang/es_es.snbt`, `lang/fr_fr.snbt`, and `lang/de_de.snbt` on par with `lang/en_us.snbt`: same keys, same ordering where practical, translated display values.

## Layout Conventions

- Keep chapter layouts readable on the FTB Quests grid.
- Prefer compact trees or hub-and-spoke clusters over long parallel columns.
- Keep high-fanout dependency quests close to their dependents so dependency lines stay short and readable.
- Use simple left-to-right or top-to-bottom progression only when it does not create long diagonal line clutter.
- Use dependencies to make progression understandable, but avoid locking unrelated player freedom.
- Give important chapter starts a clear icon and make early quests easy to understand at a glance.

## Dynamic Generation From User Directions

The user may provide directions in plain English. Convert them into concrete quest content by inferring conservative defaults:

- chapter name and filename;
- quest titles and short descriptions;
- icons from relevant items;
- item tasks and rewards where item IDs are known;
- dependencies matching the requested order;
- readable grid coordinates.

If an item, entity, structure, advancement, or mod ID is uncertain, inspect the repo first. If it still cannot be verified locally, ask for the ID or mark the assumption clearly before editing.

## Verification

After quest or KubeJS edits:

- Check SNBT syntax visually for balanced braces, brackets, and commas.
- Search for duplicate generated FTB IDs.
- Confirm every new quest title and description key exists in `lang/en_us.snbt`.
- Confirm every English quest title and description key also exists in `lang/es_es.snbt`, `lang/fr_fr.snbt`, and `lang/de_de.snbt`.
- If KubeJS was changed, launch or sync into a test instance when practical and check `latest.log` for KubeJS errors.
- For dynamic trigger bridges, test one representative quest end-to-end before expanding the pattern broadly.
