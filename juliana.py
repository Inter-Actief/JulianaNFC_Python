#!/usr/bin/python3 -u

import random
import string
import traceback

from smartcard.CardConnection import CardConnection
from smartcard.CardConnectionObserver import CardConnectionObserver
from smartcard.CardMonitoring import CardMonitor, CardObserver

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from subprocess import Popen


def debug_desfire_version(version):
    # Referenced from: 
    # https://github.com/EsupPortail/esup-nfc-tag-server/blob/d27858c653635093b670d1a5a68f742b51176207/src/main/java/nfcjlib/core/DESFireEV1.java#L2106
    # hardware info
    print("Hardware info")
    print("       vendor: {:02x}".format(version[0]), end="")
    print(" (NXP)" if version[0] == 0x04 else '')
    print(" type/subtype: {:02x}/{:02x}".format(version[1], version[2]))
    print("      version: {}.{}".format(version[3], version[4]))
    exp = (version[5] >> 1);
    print(" storage size: {}".format(2 ** exp), end="")
    print(" bytes" if version[5] & 0x01 == 0 else " to {} bytes".format(2 ** (exp + 1)))
    print("     protocol: 0x{:02x}".format(version[6]))
    print("            ISO 14443-3 and ISO 14443-4" if version[6] == 0x05 else "")

    # software info
    print("Software info")
    print("       vendor: {:02x}".format(version[7]), end="")
    print(" (NXP)" if version[7] == 0x04 else '')
    print(" type/subtype: {:02x}/{:02x}".format(version[8], version[9]))
    print("      version: {}.{}".format(version[10], version[11]))
    exp = (version[12] >> 1);
    print(" storage size: {}".format(2 ** exp), end="")
    print(" bytes" if version[12] & 0x01 == 0 else " to {} bytes".format(2 ** (exp + 1)))
    print("     protocol: 0x{:02x}".format(version[13]))
    print("            ISO 14443-3 and ISO 14443-4" if version[6] == 0x05 else "")

    # other info
    print("Other info")
    print(" batch number: {}".format(":".join("{:02x}".format(x) for x in version[21:26])))
    print("          UID: {}".format(":".join("{:02x}".format(x) for x in version[14:21])))
    print("   production: week 0x{:02x}, year 0x{:02x}  ???".format(version[22], version[23]))


def process_desfire_response(cardconnection, version_info):
    try:
        if version_info[10] not in [0x01, 0x02]:
            debug_desfire_version(version_info)
            raise IndexError("Only DESFire EV1 and EV2 supported for now (found version {})".format(version_info[10]))

        uid = version_info[14:21]

        if all(x == 0x00 for x in uid):
            raise IndexError("DESFire EV{} card with all-zero UID found (random UID mode)".format(version_info[10]))

        send_nfc_tag({
            # "type": "iso-a",
            "uid": ":".join("{:02x}".format(x) for x in uid),
            "atqa": "{:02x}:{:02x}".format(0x03, 0x44),  # Only with iso-a
            "sak": "{:02x}".format(0x20),  # Only with iso-a
        })

        # Beep card reader and set LED to green.
        cardconnection.transmit(bytes=[0xFF, 0x00, 0x40, 0x34, 0x04, 0x02, 0x02, 0x01, 0x01])
    except IndexError:
        traceback.print_exc()
        print("Invalid card scan, please retry")


def process_classic_response(cardconnection, rdata, sw1, sw2):
    try:
        sak = rdata[6]
        uidlen = rdata[7]
        atqa = rdata[4:6]
        uid = rdata[8:(8 + uidlen)]

        send_nfc_tag({
            # "type": "iso-a",
            "uid": ":".join("{:02x}".format(x) for x in uid),
            "atqa": "{:02x}:{:02x}".format(atqa[0], atqa[1]),  # Only with iso-a
            "sak": "{:02x}".format(sak),  # Only with iso-a
        })

        # Beep card reader and set LED to green.
        cardconnection.transmit(bytes=[0xFF, 0x00, 0x40, 0x34, 0x04, 0x02, 0x02, 0x01, 0x01])
    except IndexError:
        traceback.print_exc()
        print("Invalid card scan, please retry")


class RfidCardObserver(CardObserver):
    def __init__(self):
        super().__init__()
        self.buzzer_off = False

    def update(self, observable, actions):
        (added, removed) = actions
        if added:
            for card in added:
                conn = card.createConnection()
                conn.connect()

                # Set card reader LED to orange.
                conn.transmit(bytes=[0xFF, 0x00, 0x40, 0x3C, 0x04, 0x01, 0x01, 0x01, 0x00])
                # If we didn't turn the buzzer off yet, disable it.
                conn.transmit(bytes=[0xFF, 0x00, 0x52, 0x00, 0x00])
                # if not self.buzzer_off:
                #     self.buzzer_off = True

                # Ask the card for its ATR
                atr_str = "".join("{:02x}".format(x) for x in conn.getATR())
                if atr_str == "3b8180018080":
                    # DESFire card, retrieve data in a different way
                    # References:
                    # - https://stackoverflow.com/questions/29819356/apdu-for-getting-uid-from-mifare-desfire
                    # - https://stackoverflow.com/questions/40101316/whats-the-difference-between-desfire-and-desfire-ev1-cards
                    # - https://stackoverflow.com/questions/15967255/how-to-get-sak-to-identify-smart-card-type-using-java
                    # - https://smartcard-atr.apdu.fr/parse?ATR=3b8180018080
                    version_info = []
                    try:
                        rdata, s1, s2 = conn.transmit(bytes=[0x90, 0x60, 0x00, 0x00, 0x00])
                        version_info.extend(rdata)
                        rdata, s1, s2 = conn.transmit(bytes=[0x90, 0xAF, 0x00, 0x00, 0x00])
                        version_info.extend(rdata)
                        rdata, s1, s2 = conn.transmit(bytes=[0x90, 0xAF, 0x00, 0x00, 0x00])
                        version_info.extend(rdata)
                        process_desfire_response(conn, version_info)
                    except IndexError:
                        traceback.print_exc()
                        print("Invalid card scan, please retry")
                else:
                    # Probably Mifare Classic, ask it for its UID, ATQA and SAK
                    rdata, s1, s2 = conn.transmit(bytes=[0xFF, 0x00, 0x00, 0x00, 0x04, 0xD4, 0x4A, 0x01, 0x00])
                    process_classic_response(conn, rdata, s1, s2)


app = Flask(__name__)
app.debug = False
app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
socketio = SocketIO(app, cors_allowed_origins='*')


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('nfc_echo_test')
def on_message(message):
    print("sending back:", message)
    emit('nfc_echo_test_response', {'data': message['data']})


def send_nfc_tag(card):
    print("Sending:", card)
    Popen(["/bin/su", "kiosk", "-s", "/bin/bash", "-c", "/usr/bin/xset -display :0 dpms force on"])
    socketio.emit('nfc_read', card)


if __name__ == '__main__':
    monitor = CardMonitor()
    observer = RfidCardObserver()
    monitor.addObserver(observer)
    socketio.run(app, port=3000)

