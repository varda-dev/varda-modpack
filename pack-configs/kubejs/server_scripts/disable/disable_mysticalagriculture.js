//ignored: true
//priority: 0
//requires: mysticalagriculture

ServerEvents.recipes(event => {

	const disabledRecipes = [
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
		'mysticalagriculture:tertium_upgrade'
	]
	disabledRecipes.forEach(id => event.remove({ output: id }))
})
