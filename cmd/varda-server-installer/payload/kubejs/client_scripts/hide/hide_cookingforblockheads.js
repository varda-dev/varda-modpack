//ignored: true
//requires: cookingforblockheads

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'cookingforblockheads:heating_unit'
  ]

  console.info(`[KubeJS] Removing ${items.length} Cooking for Blockheads recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
