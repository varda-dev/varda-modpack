//ignored: true
//requires: waystones

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = Ingredient.of('@waystones').itemIds

  console.info(`[KubeJS] Removing ${items.length} Waystones recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
