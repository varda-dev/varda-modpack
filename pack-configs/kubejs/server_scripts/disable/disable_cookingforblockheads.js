//priority: 0
//requires: cookingforblockheads

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'cookingforblockheads:heating_unit'
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} Cooking for Blockheads recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
