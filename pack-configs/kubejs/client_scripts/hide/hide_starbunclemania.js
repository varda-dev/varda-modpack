//priority: 0
//requires: starbunclemania

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'starbunclemania:star_battery'
  ]

  console.info(`[KubeJS] Removing ${items.length} Starbunclemania entries from recipe viewer`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing recipe viewer entry: ${id}`)
    event.remove(id)
  })
})