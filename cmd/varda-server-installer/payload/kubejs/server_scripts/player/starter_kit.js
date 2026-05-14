//requires: ars_nouveau

PlayerEvents.loggedIn(event => {
  const pData = event.player.persistentData

  if (!pData.getBoolean('vardaStarterKit')) {
    pData.putBoolean('vardaStarterKit', true)

    event.player.give('ftbquests:book')
  }
})
