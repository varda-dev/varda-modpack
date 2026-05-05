//priority: 0
//requires: waystones

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = Ingredient.of('@waystones').itemIds

  console.info(`[KubeJS] Removing ${items.length} Waystones entries from recipe viewer`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing recipe viewer entry: ${id}`)
    event.remove(id)
  })
})