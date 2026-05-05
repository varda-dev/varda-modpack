//priority: 0
//requires: ars_nouveau

PlayerEvents.loggedIn(event => {
  const pData = event.player.persistentData

  if (!pData.getBoolean('vardaStarterKit')) {
    pData.putBoolean('vardaStarterKit', true)

    event.player.give('ars_nouveau:novice_spell_book')
    event.player.give('ars_nouveau:arcanist_hood')
    event.player.give('10x minecraft:apple')
  }
})