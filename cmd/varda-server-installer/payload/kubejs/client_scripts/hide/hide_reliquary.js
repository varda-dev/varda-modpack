//ignored: true
//requires: reliquary

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = Ingredient.of('@reliquary').itemIds.filter(id =>
    /^reliquary:(handgun|.*_assembly|magazines\/.*|bullets\/.*)$/.test(id)
  )

  console.info(`[KubeJS] Removing ${items.length} Reliquary recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
