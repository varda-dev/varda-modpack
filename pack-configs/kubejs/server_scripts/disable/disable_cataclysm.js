//ignored: true
//priority: 0
//requires: cataclysm

ServerEvents.recipes(event => {
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
		'cataclysm:stonecutting/stone_tile_wall_from_stonecutting'
	]

	badRecipes.forEach(id => {
		try {
			event.remove({ id: id })
		} catch (err) {
			console.log(`[KubeJS] Could not remove recipe ${id}: ${err}`)
		}
	})
})