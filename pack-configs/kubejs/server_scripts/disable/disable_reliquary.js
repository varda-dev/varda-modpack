//priority: 0
//requires: reliquary

ServerEvents.recipes(event => {
	const disabledRecipes = [
		'reliquary:barrel_assembly',
		'reliquary:grip_assembly',
		'reliquary:hammer_assembly',
		'reliquary:handgun',
		/reliquary:magazines\/.*/,
		/reliquary:bullets\/.*/,
	]
	disabledRecipes.forEach(id => event.remove({ output: id }))
})
