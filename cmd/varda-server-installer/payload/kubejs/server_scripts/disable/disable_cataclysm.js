//requires: cataclysm

ServerEvents.recipes(event => {
	const disabledRecipes = [
    'cataclysm:mechanical_fusion_anvil',
		'cataclysm:meat_shredder',
		'cataclysm:laser_gatling',
		'cataclysm:wither_assault_shoulder_weapon',
		'cataclysm:void_assault_shoulder_weapon'
  ]

	console.info(`[KubeJS] Removing ${disabledRecipes.length} L_Ender's Cataclysm recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
