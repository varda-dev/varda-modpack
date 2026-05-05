//priority: 0
//requires: reliquary

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = Ingredient.of('@reliquary').itemIds.filter(id =>
    /^reliquary:(handgun|.*_assembly|magazines\/.*|bullets\/.*)$/.test(id)
  )

  console.info(`[KubeJS] Removing ${items.length} Reliquary entries from recipe viewer`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing recipe viewer entry: ${id}`)
    event.remove(id)
  })
})