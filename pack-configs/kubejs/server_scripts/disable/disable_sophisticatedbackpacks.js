//priority: 0
//requires: sophisticatedbackpacks

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'sophisticatedbackpacks:battery_upgrade',
    'sophisticatedbackpacks:infinity_upgrade',
    'sophisticatedbackpacks:survival_infinity_upgrade'
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} Sophisticated Backpacks recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
