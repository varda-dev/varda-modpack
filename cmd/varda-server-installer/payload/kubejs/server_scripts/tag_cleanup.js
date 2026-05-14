//priority: -50

const log = message => console.info(`[KubeJS/tag-cleanup] ${message}`)

ServerEvents.tags('item', event => {
  log('Running item tag cleanup')

  event.remove('werewolves:werewolf_food', 'relics:infinity_ham')
  log('Removed relics:infinity_ham from werewolves:werewolf_food')

  const lichStaves = [
    'ars_zero:staff_enchanters',
    'ars_zero:staff_archmage',
    'ars_zero:staff_necromancer',
    'ars_zero:staff_lich',
    'ars_zero:staff_demonbane',
    'ars_zero:staff_geometrize',
    'ars_zero:staff_convergence',
    'ars_zero:staff_lakes',
    'ars_zero:staff_switcheroo'
  ]

  event.remove('ars_zero:lich_staves', lichStaves)
  log(`Removed ${lichStaves.length} entries from ars_zero:lich_staves`)
})
