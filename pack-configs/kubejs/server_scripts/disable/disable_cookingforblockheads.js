//priority: 0
//requires: cookingforblockheads

ServerEvents.recipes(event => {
	const disabledRecipes = [
		'cookingforblockheads:heating_unit'
	]
	disabledRecipes.forEach(id => event.remove({ output: id }))
})
