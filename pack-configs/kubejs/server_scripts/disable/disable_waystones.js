//priority: 0
//requires: waystones

ServerEvents.recipes(event => {
  const disabledRecipeFilters = [
    {
      label: 'output /^waystones:.*/',
      filter: { output: /^waystones:.*/ }
    },
    {
      label: 'mod waystones',
      filter: { mod: 'waystones' }
    }
  ]

  console.info(`[KubeJS] Removing ${disabledRecipeFilters.length} Waystones recipes`)

  disabledRecipeFilters.forEach(entry => {
    console.info(`[KubeJS] Removing recipe filter: ${entry.label}`)
    event.remove(entry.filter)
  })
})
