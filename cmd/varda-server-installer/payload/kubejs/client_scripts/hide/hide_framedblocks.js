//ignored: true
//requires: framedblocks

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'framedblocks:powered_framing_saw'
  ]

  console.info(`[KubeJS] Removing ${items.length} FramedBlocks recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
