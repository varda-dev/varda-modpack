//requires: mcwdoors

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'mcwdoors:metal_door',
    'mcwdoors:metal_warning_door',
    'mcwdoors:metal_hospital_door',
    'mcwdoors:metal_reinforced_door',
    'mcwdoors:metal_windowed_door',
    'mcwdoors:jail_door'
  ]

  console.info(`[KubeJS] Removing ${items.length} Macaw's Doors recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
