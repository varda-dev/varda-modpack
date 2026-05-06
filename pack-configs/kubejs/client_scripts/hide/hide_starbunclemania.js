//requires: starbunclemania

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'starbunclemania:star_battery'
  ]

  console.info(`[KubeJS] Removing ${items.length} Starbunclemania recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
