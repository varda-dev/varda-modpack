//requires: ftbquests

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'ftbquests:loot_crate_opener',
    'ftbquests:screen_1',
    'ftbquests:screen_3',
    'ftbquests:screen_5',
    'ftbquests:screen_7',
    'ftbquests:task_screen_configurator'
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} FTB Quests recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
