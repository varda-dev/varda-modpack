// priority: 0

ServerEvents.recipes(event => {

	const disabledRecipes = [
		'framedblocks:powered_framing_saw',
		'gag:no_solicitors',
		'gag:time_sand_pouch',
		'mysticaladaptations:insanium_reprocessor',
		'mysticalagriculture:awakended_supremium_upgrade',
		'mysticalagriculture:furnace',
		'mysticalagriculture:flight_augment',
		'mysticalagriculture:harvester',
		'mysticalagriculture:imperium_upgrade',
		'mysticalagriculture:inferium_upgrade',
		'mysticalagriculture:machine_frame',
		'mysticalagriculture:prudentium_upgrade',
		'mysticalagriculture:seed_reprocessor',
		'mysticalagriculture:soul_extractor',
		'mysticalagriculture:soulium_spawner',
		'mysticalagriculture:supremium_upgrade',
		'mysticalagriculture:tertium_upgrade',
		'reliquary:barrel_assembly',
		'reliquary:bullets',
		'reliquary:grip_assembly',
		'reliquary:hammer_assembly',
		'reliquary:handgun',
		'reliquary:magazines',
		'sophisticatedbackpacks:battery_upgrade',
		'sophisticatedbackpacks:infinity_upgrade',
		'sophisticatedbackpacks:survival_infinity_upgrade',
		'starbunclemania:star_battery',
	]
	disabledRecipes.forEach(id => event.remove({ output: id }))

	const badRecipes = [
		'cataclysm:blasting/ancient_metal_nugget_from_blasting',
		'cataclysm:blasting/black_steel_nugget_from_blasting',
		'cataclysm:stonecutting/chiseled_end_stone_bricks_from_stonecutting',
		'cataclysm:stonecutting/chiseled_obsidian_bricks_from_stonecutting',
		'cataclysm:stonecutting/chiseled_purpur_block_from_stonecutting',
		'cataclysm:stonecutting/chiseled_stone_brick_pillar_from_stonecutting',
		'cataclysm:stonecutting/end_stone_pillar_from_stonecutting',
		'cataclysm:stonecutting/frosted_stone_brick_slab_from_stonecutting',
		'cataclysm:stonecutting/frosted_stone_brick_stairs_from_stonecutting',
		'cataclysm:stonecutting/frosted_stone_brick_wall_from_stonecutting',
		'cataclysm:stonecutting/obsidian_brick_wall_from_stonecutting',
		'cataclysm:stonecutting/polished_end_stone_stairs_from_stonecutting',
		'cataclysm:stonecutting/purpur_wall_from_stonecutting',
		'cataclysm:stonecutting/quartz_brick_wall_from_stonecutting',
		'cataclysm:stonecutting/stone_tile_stairs_from_stonecutting',
		'cataclysm:stonecutting/stone_tile_wall_from_stonecutting',
	]
	badRecipes.forEach(id => event.remove({ id: id }))
})

console.info('Varda: Loaded crafting alter/disable script')