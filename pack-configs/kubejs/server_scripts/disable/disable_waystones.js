//priority: 0
//requires: waystones

ServerEvents.recipes(event => {
  event.remove({ output: /^waystones:.*/ })
  event.remove({ mod: 'waystones' })
})

