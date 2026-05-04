//priority: 0
//requires: gag

ServerEvents.recipes(event => {
	const disabledRecipes = [
		'gag:no_solicitors'
	]
	disabledRecipes.forEach(id => event.remove({ output: id }))
})
