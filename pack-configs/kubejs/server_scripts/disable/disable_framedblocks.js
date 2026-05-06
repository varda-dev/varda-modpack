//ignored: true
//requires: framedblocks

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'framedblocks:powered_framing_saw'
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} FramedBlocks recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
