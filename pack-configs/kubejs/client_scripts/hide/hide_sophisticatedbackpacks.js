//priority: 0
//requires: sophisticatedbackpacks

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'sophisticatedbackpacks:battery_upgrade',
    'sophisticatedbackpacks:infinity_upgrade',
    'sophisticatedbackpacks:survival_infinity_upgrade'
  ]

  console.info(`[KubeJS] Removing ${items.length} Sophisticated Backpacks entries from recipe viewer`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing recipe viewer entry: ${id}`)
    event.remove(id)
  })
})