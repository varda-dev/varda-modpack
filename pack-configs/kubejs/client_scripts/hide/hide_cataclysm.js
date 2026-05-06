//requires: cataclysm

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'cataclysm:mechanical_fusion_anvil',
		'cataclysm:meat_shredder',
		'cataclysm:laser_gatling',
		'cataclysm:wither_assault_shoulder_weapon',
		'cataclysm:void_assault_shoulder_weapon'
  ]

  console.info(`[KubeJS] Removing ${items.length} L_Ender's Cataclysm recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
