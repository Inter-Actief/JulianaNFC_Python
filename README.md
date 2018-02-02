# JulianaNFC
JulianaNFC is een Python-programmaatje dat pollt voor NFC tags en deze vervolgens over een WebSocket verstuurt. Werkt alleen onder Linux voor zover bekend.

## Hoe dan?
Installeer onder Linux de PC/SC Smart Card daemon ( [PCSClite](https://pcsclite.alioth.debian.org/pcsclite.html) - [Debian PKG](https://packages.debian.org/source/stretch/pcsc-lite) ) en zorg dat deze gestart is. Installeer de requirements uit requirements.txt en start juliana.py. Vanuit een browser connect je met de WebSocket.

    socket = new WebSocket("ws://localhost:3000", "nfc");

Als er een kaart wordt gescand ontvang je een JSON-object met kaartinfo over de socket.

    {"atqa":"12:34", "uid":"ab:cd:ef:gh", "sak":"56"}

En dat is alles wat JulianaNFC doet.

## Bugs en to-do's

WebSockets zijn zéér gebrekkig geïmplementeerd. Zodra iets niet volgens plan gebeurt crasht JulianaNFC.
