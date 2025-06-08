//priority: 0
//requires: gag

ServerEvents.recipes(event => {
	const disabledRecipes = [
		'gag:no_solicitors',
		'gag:time_sand_pouch'
	]
	disabledRecipes.forEach(id => event.remove({ output: id }))
})
