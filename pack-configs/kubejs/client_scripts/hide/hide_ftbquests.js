//requires: ftbquests

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'ftbquests:loot_crate_opener',
    'ftbquests:barrier',
    'ftbquests:stage_barrier',
    'ftbquests:detector',
    'ftbquests:screen_1',
    'ftbquests:screen_3',
    'ftbquests:screen_5',
    'ftbquests:screen_7',
    'ftbquests:task_screen_configurator'
  ]

  console.info(`[KubeJS] Removing ${items.length} FTB Quests recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
