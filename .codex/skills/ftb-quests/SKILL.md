---
name: ftb-quests
description: >
  Varda FTB Quests workflow skill. Use for creating or editing Varda quest content,
  chapter layout, translations, and KubeJS bridge logic for quest completion.
---

Use this skill for Varda quest book work. Quest source of truth lives in AGENTS.md and pack-configs, not pack-docs.

## Source Files

- `pack-configs/config/ftbquests/quests/data.snbt`
- `pack-configs/config/ftbquests/quests/chapter_groups.snbt`
- `pack-configs/config/ftbquests/quests/chapters/*.snbt`
- `pack-configs/config/ftbquests/quests/lang/en_us.snbt`
- `pack-configs/config/ftbquests/quests/lang/es_es.snbt`
- `pack-configs/config/ftbquests/quests/lang/fr_fr.snbt`
- `pack-configs/config/ftbquests/quests/lang/de_de.snbt`
- `pack-configs/kubejs/server_scripts/` for dynamic progression bridges

## Design Intent

- Ars Nouveau core. Quests teach source progression, exploration, rituals, familiars, storage, and building.
- No RF/FE progression. Rewards should reinforce magic, source, exploration, building, or QoL.
- Quest book guides. Not forced checklist.
- Vanilla advancement tabs support onboarding. Ars Nouveau chapters remain main path.
- `The Tattered Path` first group. `The Familiar Trail` above `The Hidden Thread`.
- Preserve lore and pack proper nouns such as `Varda`, but localize surrounding title words naturally.

## Workflow

- Use FTB Quests for visible book layer: chapter groups, ordering, layout, titles, descriptions, icons, item tasks, item rewards, dependencies.
- Prefer `lang/en_us.snbt` for player-facing text.
- Keep `es_es`, `fr_fr`, and `de_de` aligned with English keys.
- Use KubeJS for boss kills, dimension entry, structure/biome/location milestones, custom flags, conditional rewards, and quest bridge logic.
- Add `//requires: modid` to mod-specific KubeJS files.

## IDs And Layout

- Use uppercase 16-character hex IDs for chapter, quest, task, reward IDs.
- Keep filenames lowercase with underscores.
- Preserve existing IDs unless replacing intentionally.
- Prefer compact hub-and-spoke layout or short progression trees.
- Keep dependency lines short and readable.

## Bridge Patterns

- KubeJS grants custom advancement, FTB Quests tracks advancement.
- KubeJS gives hidden marker item, FTB Quests tracks item.
- KubeJS runs FTB Quests progress command only if verified in current pack version.
- KubeJS handles reward directly when FTB Quests only needs visible guidance.

## Verification

- Check SNBT braces, commas, and brackets.
- Search for duplicate FTB IDs.
- Verify every new text key exists in `en_us` and matching translated files.
- If KubeJS changed, test in instance and check `latest.log`.
- For bridge logic, test one quest end-to-end before broad rollout.
