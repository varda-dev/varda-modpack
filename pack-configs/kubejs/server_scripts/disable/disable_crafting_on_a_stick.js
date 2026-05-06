//requires: crafting_on_a_stick

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'crafting_on_a_stick:loom',
    'crafting_on_a_stick:grindstone',
    'crafting_on_a_stick:cartography_table',
    'crafting_on_a_stick:stonecutter',
    'crafting_on_a_stick:smithing_table',
    'crafting_on_a_stick:anvil',
    'crafting_on_a_stick:chipped_anvil',
    'crafting_on_a_stick:damaged_anvil'
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} Crafting on a Stick recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
