// requires: handcrafted

ServerEvents.recipes(event => {
  const colors = [
    'white', 'orange', 'magenta', 'light_blue',
    'yellow', 'lime', 'pink', 'gray',
    'light_gray', 'cyan', 'purple', 'blue',
    'brown', 'green', 'red', 'black'
  ]

  console.info('[KubeJS] Loading Handcrafted sheet recipe overrides...')

  colors.forEach(color => {
    const output = `handcrafted:${color}_sheet`
    const input = `minecraft:${color}_wool`
    const recipeId = `kubejs:handcrafted_${color}_sheet_fixed`

    console.info(`[KubeJS] Removing existing recipe(s) for ${output}`)
    event.remove({ output: output })

    console.info(`[KubeJS] Adding fixed top-left recipe for ${output} using ${input}`)
    event.shaped(output, [
      'WW ',
      'W  ',
      '   '
    ], {
      W: input
    }).id(recipeId)
  })

  console.info(`[KubeJS] Finished overriding ${colors.length} Handcrafted sheet recipes.`)
})
