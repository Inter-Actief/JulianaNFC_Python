#!/usr/bin/python3 -u

import random
import string
import traceback

from smartcard.CardConnection import CardConnection
from smartcard.CardConnectionObserver import CardConnectionObserver
from smartcard.CardMonitoring import CardMonitor, CardObserver

from flask import Flask, render_template
from flask_socketio import SocketIO, emit


class RfidCardConnectionObserver(CardConnectionObserver):
    def update(self, cardconnection, cardconnectionevent):
        if cardconnectionevent.type == "response" and cardconnectionevent.args[0]:
            try:
                sak = cardconnectionevent.args[0][6]
                uidlen = cardconnectionevent.args[0][7]
                atqa = cardconnectionevent.args[0][4:6]
                uid = cardconnectionevent.args[0][8:(8 + uidlen)]

                send_nfc_tag({
                    # "type": "iso-a",
                    "uid": ":".join("{:02x}".format(x) for x in uid),
                    "atqa": "{:02x}:{:02x}".format(atqa[0], atqa[1]),  # Only with iso-a
                    "sak": "{:02x}".format(sak),  # Only with iso-a
                })

                # Beep card reader and set LED to green.
                cardconnection.transmit(bytes=[
                    0xFF, 0x00, 0x40, 0x34, 0x04, 0x02, 0x02, 0x01, 0x01
                ], protocol=CardConnection.T0_protocol)
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
                c_obs = RfidCardConnectionObserver()
                conn.addObserver(c_obs)
                conn.connect(protocol=CardConnection.T0_protocol)

                # Set card reader LED to orange.
                conn.transmit(bytes=[0xFF, 0x00, 0x40, 0x3C, 0x04, 0x01, 0x01, 0x01, 0x00])
                # If we didn't turn the buzzer off yet, disable it.
                conn.transmit(bytes=[0xFF, 0x00, 0x52, 0x00, 0x00], protocol=CardConnection.T0_protocol)
                # if not self.buzzer_off:
                #     self.buzzer_off = True

                # Ask the card for its UID.
                conn.transmit(bytes=[0xFF, 0x00, 0x00, 0x00, 0x04, 0xD4, 0x4A, 0x01, 0x00],
                              protocol=CardConnection.T0_protocol)


app = Flask(__name__)
app.debug = False
app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('nfc_echo_test')
def on_message(message):
    print("sending back:", message)
    emit('nfc_echo_test_response', {'data': message['data']})


def send_nfc_tag(card):
    print("Sending:", card)
    socketio.emit('nfc_read', card)


if __name__ == '__main__':
    monitor = CardMonitor()
    observer = RfidCardObserver()
    monitor.addObserver(observer)
    socketio.run(app)
