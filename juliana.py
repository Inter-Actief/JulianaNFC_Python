import json
import queue
import sys

import asyncio

import time
import traceback

import websockets
from smartcard.CardConnection import CardConnection
from smartcard.CardConnectionObserver import CardConnectionObserver
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toHexString


monitor = None


class RfidCardConnectionObserver(CardConnectionObserver):
    def __init__(self, connection, queue):
        super(RfidCardConnectionObserver, self).__init__()
        self.connection = connection
        self.cards = queue

    def update(self, cardconnection, cardconnectionevent):
        if cardconnectionevent.type == "response" and cardconnectionevent.args[0]:
            try:
                sak = cardconnectionevent.args[0][6]
                uidlen = cardconnectionevent.args[0][7]
                atqa = cardconnectionevent.args[0][4:6]
                uid = cardconnectionevent.args[0][8:(8+uidlen)]
                data = json.dumps({
                    "type": "iso-a",
                    "uid": ":".join("{:02x}".format(x) for x in uid),
                    "atqa": "{:02x}:{:02x}".format(atqa[0], atqa[1]),  # Only with iso-a
                    "sak": "{:02x}".format(sak),  # Only with iso-a
                })
                self.cards.put(data)
                # Beep card reader and set LED to green.
                cardconnection.transmit(bytes=[
                    0xFF, 0x00, 0x40, 0x34, 0x04, 0x02, 0x02, 0x01, 0x01
                ], protocol=CardConnection.T0_protocol)
            except IndexError:
                traceback.print_exc()
                print("Invalid card scan, please retry")


class RfidCardObserver(CardObserver):
    def __init__(self, websocket):
        super().__init__()
        self.socket = websocket
        self.cards = queue.Queue()
        self.buzzer_off = False

    def update(self, observable, actions):
        (added, removed) = actions
        if added:
            for card in added:
                conn = card.createConnection()
                c_obs = RfidCardConnectionObserver(conn, self.cards)
                conn.addObserver(c_obs)
                conn.connect(protocol=CardConnection.T0_protocol)

                # Set card reader LED to orange.
                conn.transmit(bytes=[0xFF, 0x00, 0x40, 0x3C, 0x04, 0x01, 0x01, 0x01, 0x00])
                # If we didn't turn the buzzer off yet, disable it.
                if not self.buzzer_off:
                    conn.transmit(bytes=[0xFF, 0x00, 0x52, 0x00, 0x00], protocol=CardConnection.T0_protocol)
                    self.buzzer_off = True

                # Ask the card for its UID.
                conn.transmit(bytes=[0xFF, 0x00, 0x00, 0x00, 0x04, 0xD4, 0x4A, 0x01, 0x00], protocol=CardConnection.T0_protocol)

    def get_card(self):
        return self.cards.get()


async def websocket_handler(websocket, path):
    print("Connection from {}".format(websocket.remote_address))

    observer = RfidCardObserver(websocket)
    monitor.addObserver(observer)

    try:
        while True:
            card = observer.get_card()
            if card is not None:
                print("Card: {}".format(card))
                await websocket.send(card)
    except Exception as e:
        print("Error: {}".format(e))
        monitor.deleteObserver(observer)
        print("Disconnect from {}".format(websocket.remote_address))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if "--help" in sys.argv or "-h" in sys.argv:
            print("{} - JulianaNFC Python Card Reader".format(sys.argv[0]))
            print("Usage: {} [OPTIONS]".format(sys.argv[0]))
            print("  -h, --help       Show this help text.")
            print("  -g, --gui        Show the GUI window.")
            sys.exit(0)
        elif "--gui" in sys.argv or "-g" in sys.argv:
            print("Starting in GUI mode...")
        else:
            print("Starting in CLI mode...")
    else:
        print("Starting in CLI mode...")
    monitor = CardMonitor()
    asyncio.get_event_loop().run_until_complete(websockets.serve(websocket_handler, 'localhost', 3000))
    asyncio.get_event_loop().run_forever()
