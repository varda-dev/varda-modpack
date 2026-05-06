//ignored: true
//requires: gag

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'gag:no_solicitors'
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} Gag recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
