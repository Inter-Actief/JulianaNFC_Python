# JulianaNFC
JulianaNFC is een Win32-programmaatje dat pollt voor NFC tags en deze vervolgens over een WebSocket verstuurt.

## Hoe dan?
Je start JulianaNFC.exe (eventueel met de command line switch '/toeter' voor extra escalatie). Vanuit een browser connect je met de WebSocket.

    socket = new WebSocket("ws://localhost:3000", "nfc");

Als er een kaart wordt gescand ontvang je een JSON-object met kaartinfo over de socket.

    {"atqa":"12:34", "uid":"ab:cd:ef:gh", "sak":"56"}

En dat is alles wat JulianaNFC doet.

## Bugs en to-do's

WebSockets zijn zéér gebrekkig geïmplementeerd. Zodra iets niet volgens plan gebeurt crasht JulianaNFC.
