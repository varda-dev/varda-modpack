//ignored: true
//requires: sophisticatedbackpacks

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'sophisticatedbackpacks:battery_upgrade',
    'sophisticatedbackpacks:infinity_upgrade',
    'sophisticatedbackpacks:survival_infinity_upgrade'
  ]

  console.info(`[KubeJS] Removing ${items.length} Sophisticated Backpacks recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
