# JulianaNFC
JulianaNFC is een Python-programmaatje voor Windows en Linux dat pollt voor NFC tags en deze vervolgens over een WebSocket verstuurt.

## Hoe dan?

### Windows

#### Requirements
NFCPy heeft libusb nodig om generieke toegang te krijgen tot 
USB apparaten, wat normaal niet is toegestaan onder Windows. 
(instructies gekopieerd van [NFCPy](https://nfcpy.readthedocs.io/en/latest/topics/get-started.html#installation))

- Download [Zadig](http://zadig.akeo.ie/)
- Connect your NFC device
- Run the downloaded executable
- Click Options -> List All Devices
- Select your NFC reading/writing device from the list
- Select the WinUSB driver from the other drop down and install it (Replace Driver)


- Then, install libusb:
  - Download [libusb](http://libusb.info/) (Downloads -> Latest Windows Binaries).
  - Unpack the 7z archive (you may use 7zip).
  - For 32-bit Windows:
    - Copy VS2015-Win32\dll\libusb-1.0.dll to C:\Windows\System32.
  - For 64-bit Windows:
    - Copy VS2015-x64\dll\libusb-1.0.dll to C:\Windows\System32.
    - Copy VS2015-Win32\dll\libusb-1.0.dll to C:\Windows\SysWOW64.

#### JulianaNFC
Download en start JulianaNFC_Python:
- Download de [release executable](https://github.com/Inter-Actief/JulianaNFC_Python/releases) voor Windows (`JulianaNFC_vX.X.exe`)
- Zet hem op een mooi plekje neer
- Start daarna `JulianaNFC_vX.X.exe`, de GUI zal starten.

### Linux

#### Requirements
- Blacklist de `pn533` en `pn533_usb` kernel modules en herstart de PC.
  ```bash
  » cat /etc/modprobe.d/blacklist-libnfc.conf
  blacklist pn533
  blacklist pn533_usb
  ```

#### JulianaNFC - Optie 1
- Download de [release executable](https://github.com/Inter-Actief/JulianaNFC_Python/releases) voor Linux (`JulianaNFC_linux_vX.X`)
- Zet hem op een mooi plekje neer
- Start het executable bestand `JulianaNFC_linux_vX.X`, de GUI zal starten. (draai het met de `-h` flag voor CLI-opties)

#### JulianaNFC - Optie 2
- Clone of download de code van github (`git clone git@github.com:Inter-Actief/JulianaNFC_Python.git`)
- Maak een virtualenv als je dat graag wilt en activeer deze (`python3 -m venv venv; source ./venv/bin/activate`)
- Installeer de requirements uit requirements.txt (`pip install -r requirements.txt`)
- Voer `python juliana.py` uit, de GUI zal starten. (zie `juliana.py -h` voor CLI-opties)

### Websocket
Vanuit een browser connect je met de WebSocket.

    socket = new WebSocket('ws://localhost:3000');
    socket.onmessage = function (event) {
        var rfid = JSON.parse(event.data);
        console.log("Tag scanned!");
        console.log(rfid);
    };

Als er een kaart wordt gescand ontvang je over de websocket een JSON-object (in het veld `event.data` hierboven) met kaartinfo over de socket.

    {"type": "iso-x", "atqa":"12:34", "uid":"ab:cd:ef:gh", "sak":"56"}

En dat is alles wat JulianaNFC doet.

## Bugs en to-do's
Niks bekend. Maak hier nieuwe tickets aan: https://github.com/Inter-Actief/JulianaNFC_Python/issues

Mocht de kaartlezer ineens niet meer werken, dan kan je hem opnieuw inpluggen. JulianaNFC zou hem dan opnieuw moeten detecteren.

## Package bouwen
- Zoek een computer met het gewenste doelbesturingssysteem en installeer Python en alle requirements voor JulianaNFC.
  - Noot: Gebruik bij packagen op Windows een python-versie waarvoor een [.whl van wxPython](https://pypi.org/project/wxPython/#files) beschikbaar is, dit package zelf bouwen op Windows is lastig. 
- Installeer pyinstaller (`pip install pyinstaller`) (Getest met 5.2, maar zou met nieuwere prima moeten werken)
- Open een command prompt / terminal en ga naar de map waar JulianaNFC staat
- Verwijder de `build` en `dist` folders als deze nog bestaan van een vorige build
- Draai Pyinstaller op de specfile (`pyinstaller juliananfc.spec`)
- De build zal in de `build` folder plaatsvinden, de executable zal in de `dist` folder geplaatst worden.
