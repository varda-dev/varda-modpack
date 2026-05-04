//priority: 0
//requires: framedblocks

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'framedblocks:powered_framing_saw'
  ]

  console.info(`[KubeJS] Removing ${items.length} FramedBlocks entries from recipe viewer`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing recipe viewer entry: ${id}`)
    event.remove(id)
  })
})