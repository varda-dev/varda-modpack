//requires: starbunclemania

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'starbunclemania:star_battery'
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} Starbunclemania recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
