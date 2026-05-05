//priority: 0
//requires: cookingforblockheads

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'cookingforblockheads:heating_unit'
  ]

  console.info(`[KubeJS] Removing ${items.length} Cooking for Blockheads entries from recipe viewer`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing recipe viewer entry: ${id}`)
    event.remove(id)
  })
})