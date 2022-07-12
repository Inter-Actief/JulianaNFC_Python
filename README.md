# JulianaNFC
JulianaNFC is een Python-programmaatje voor Windows en Linux dat pollt voor NFC tags en deze vervolgens over een WebSocket verstuurt.

## Hoe dan?

### Windows
Geen requirements, Windows heeft een ingebouwde PC/SC Smart Card service.

- Download de [release executable](https://github.com/Inter-Actief/JulianaNFC_Python/releases) voor Windows (`JulianaNFC_vX.X.exe`)
- Zet hem op een mooi plekje neer
- Start daarna `JulianaNFC_vX.X.exe`, de GUI zal starten.

### Linux

#### Requirements
Installeer onder Linux de PC/SC Smart Card daemon ( [PCSClite](https://pcsclite.alioth.debian.org/pcsclite.html) - [Debian PKG](https://packages.debian.org/source/stretch/pcsc-lite) ) en zorg dat deze gestart is.

#### JulianaNFC - Optie 1
- Download de [release executable](https://github.com/Inter-Actief/JulianaNFC_Python/releases) voor Linux (`JulianaNFC_linux_vX.X`)
- Zet hem op een mooi plekje neer
- Start het executable bestand `JulianaNFC_linux_vX.X`, de GUI zal starten. (draai het met de `-h` flag voor CLI-opties)

#### JulianaNFC - Optie 2
- Clone of download de code van github
- Maak een virtualenv als je dat graag wilt
- Installeer de requirements uit requirements.txt
- Voer `python juliana.py` uit, de GUI zal starten. (zie `juliana.py -h` voor CLI-opties)

### Websocket
Vanuit een browser connect je met de WebSocket.

    socket = new WebSocket('ws://localhost:3000', 'nfc');
    socket.onmessage = function (event) {
        var rfid = JSON.parse(event.data);
        console.log("Tag scanned!");
        console.log(rfid);
    };

Als er een kaart wordt gescand ontvang je in het 'nfc_read' event een JSON-object met kaartinfo over de socket.

    {"type": "iso-x", "atqa":"12:34", "uid":"ab:cd:ef:gh", "sak":"56"}

En dat is alles wat JulianaNFC doet.

## Bugs en to-do's
Bij het scannen van sommige kaarten (i.e. ID-kaarten) breekt de NFC lezer (onder Linux). Even de lezer opnieuw inpluggen fixt het dan vaak.

## Package bouwen
- Zoek een computer met het gewenste doelbesturingssysteem en installeer Python en alle requirements voor JulianaNFC.
  - Noot: Gebruik bij packagen op Windows een python-versie waarvoor een [.whl van wxPython](https://pypi.org/project/wxPython/#files) beschikbaar is, dit package zelf bouwen op Windows is lastig. 
- Installeer pyinstaller (`pip install pyinstaller`) (Getest met 5.2, maar zou met nieuwere prima moeten werken)
- Open een command prompt / terminal en ga naar de map waar JulianaNFC staat
- Verwijder de `build` en `dist` folders als deze nog bestaan van een vorige build
- Draai Pyinstaller op de specfile (`pyinstaller juliana_nfc.spec`)
- De build zal in de `build` folder plaatsvinden, de executable zal in de `dist` folder geplaatst worden.
