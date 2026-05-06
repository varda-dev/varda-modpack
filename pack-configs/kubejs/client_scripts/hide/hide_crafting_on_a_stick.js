//requires: crafting_on_a_stick

RecipeViewerEvents.removeEntriesCompletely('item', event => {
  const items = [
    'crafting_on_a_stick:loom',
    'crafting_on_a_stick:grindstone',
    'crafting_on_a_stick:cartography_table',
    'crafting_on_a_stick:stonecutter',
    'crafting_on_a_stick:smithing_table',
    'crafting_on_a_stick:anvil',
    'crafting_on_a_stick:chipped_anvil',
    'crafting_on_a_stick:damaged_anvil'
  ]

  console.info(`[KubeJS] Removing ${items.length} Crafting on a Stick recipe entries`)

  items.forEach(id => {
    console.info(`[KubeJS] Removing entry: ${id}`)
    event.remove(id)
  })
})
