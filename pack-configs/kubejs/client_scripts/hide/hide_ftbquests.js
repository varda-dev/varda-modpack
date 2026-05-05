//priority: 0
//requires: ftbquests

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'ftbquests:loot_crate_opener',
    'ftbquests:screen_1',
    'ftbquests:screen_3',
    'ftbquests:screen_5',
    'ftbquests:screen_7',
    'ftbquests:task_screen_configurator'
  ]

  console.info(`[KubeJS] Removing ${items.length} FTB Quests entries from recipe viewer`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing recipe viewer entry: ${id}`)
    event.remove(id)
  })
})
