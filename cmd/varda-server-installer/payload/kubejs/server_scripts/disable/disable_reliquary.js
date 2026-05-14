//ignored: true
//requires: reliquary

ServerEvents.recipes(event => {
  const disabledRecipes = [
    'reliquary:barrel_assembly',
    'reliquary:grip_assembly',
    'reliquary:hammer_assembly',
    'reliquary:handgun',
    /reliquary:magazines\/.*/,
    /reliquary:bullets\/.*/
  ]

  console.info(`[KubeJS] Removing ${disabledRecipes.length} Reliquary recipes`)

  disabledRecipes.forEach(id => {
    console.info(`[KubeJS] Removing recipe output: ${id}`)
    event.remove({ output: id })
  })
})
