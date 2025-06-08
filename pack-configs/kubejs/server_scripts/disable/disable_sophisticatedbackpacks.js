//priority: 0
//requires: sophisticatedbackpacks

ServerEvents.recipes(event => {
	const disabledRecipes = [
		'sophisticatedbackpacks:battery_upgrade',
		'sophisticatedbackpacks:infinity_upgrade',
		'sophisticatedbackpacks:survival_infinity_upgrade'
	]
	disabledRecipes.forEach(id => event.remove({ output: id }))
})
