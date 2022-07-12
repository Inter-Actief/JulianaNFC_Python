#!/usr/bin/python3 -u

import os
import sys
import json
import time
import random
import string
import logging
import traceback
import threading

from datetime import datetime
from subprocess import Popen

import smartcard.System
from smartcard.CardConnection import CardConnection
from smartcard.CardConnectionObserver import CardConnectionObserver
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.ReaderMonitoring import ReaderMonitor, ReaderObserver
from smartcard.Exceptions import CardConnectionException

from flask import Flask, render_template, request
from flask_sock import Sock


APP_VERSION = "3.0"
APP_NAME = "JulianaNFC"
APP_AUTHOR = "Kevin Alberts, I.C.T.S.V. Inter-/Actief/"
APP_SUPPORT = "www@inter-actief.net"
APP_LINK = "https://github.com/Inter-Actief/JulianaNFC_Python"


DEBUG = False
HAS_GUI = False
DO_KIOSK_XSET = False
gui_app = None


logging.basicConfig(level=logging.INFO)


def print_console(message, level="info"):
    if level == "debug":
        logging.debug(message)
    elif level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)
    elif level == "critical":
        logging.critical(message)
    if HAS_GUI:
        global gui_app
        gui_app.add_message(f"[{datetime.now():%H:%M:%S}] {message}")


def resource_path(relative):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), relative)


def notify_toast(title, message, app_icon="resources/main.ico", timeout=3):
    if HAS_GUI:
        from plyer import notification
        notification.notify(title=title, message=message, app_icon=resource_path(app_icon), timeout=timeout)


def debug_desfire_version(version):
    # Referenced from: 
    # https://github.com/EsupPortail/esup-nfc-tag-server/blob/d27858c653635093b670d1a5a68f742b51176207/src/main/java/nfcjlib/core/DESFireEV1.java#L2106
    # hardware info
    print_console("Hardware info", level="debug")
    print_console("       vendor: {:02x}".format(version[0]), level="debug")
    print_console(" (NXP)" if version[0] == 0x04 else '', level="debug")
    print_console(" type/subtype: {:02x}/{:02x}".format(version[1], version[2]), level="debug")
    print_console("      version: {}.{}".format(version[3], version[4]), level="debug")
    exp = (version[5] >> 1)
    print_console(" storage size: {}".format(2 ** exp), level="debug")
    print_console(" bytes" if version[5] & 0x01 == 0 else " to {} bytes".format(2 ** (exp + 1)), level="debug")
    print_console("     protocol: 0x{:02x}".format(version[6]), level="debug")
    print_console("            ISO 14443-3 and ISO 14443-4" if version[6] == 0x05 else "", level="debug")

    # software info
    print_console("Software info", level="debug")
    print_console("       vendor: {:02x}".format(version[7]), level="debug")
    print_console(" (NXP)" if version[7] == 0x04 else '', level="debug")
    print_console(" type/subtype: {:02x}/{:02x}".format(version[8], version[9]), level="debug")
    print_console("      version: {}.{}".format(version[10], version[11]), level="debug")
    exp = (version[12] >> 1);
    print_console(" storage size: {}".format(2 ** exp), level="debug")
    print_console(" bytes" if version[12] & 0x01 == 0 else " to {} bytes".format(2 ** (exp + 1)), level="debug")
    print_console("     protocol: 0x{:02x}".format(version[13]), level="debug")
    print_console("            ISO 14443-3 and ISO 14443-4" if version[6] == 0x05 else "", level="debug")

    # other info
    print_console("Other info", level="debug")
    print_console(" batch number: {}".format(":".join("{:02x}".format(x) for x in version[21:26])), level="debug")
    print_console("          UID: {}".format(":".join("{:02x}".format(x) for x in version[14:21])), level="debug")
    print_console("   production: week 0x{:02x}, year 0x{:02x}  ???".format(version[22], version[23]), level="debug")


def process_desfire_response(cardconnection, version_info):
    try:
        if version_info[10] not in [0x01, 0x02]:
            if DEBUG:
                debug_desfire_version(version_info)
            raise IndexError("Only DESFire EV1 and EV2 supported for now (found version {})".format(version_info[10]))

        uid = version_info[14:21]

        if all(x == 0x00 for x in uid):
            raise IndexError("DESFire EV{} card with all-zero UID found (random UID mode)".format(version_info[10]))

        send_nfc_tag({
            "type": "iso-4",
            "uid": ":".join("{:02x}".format(x) for x in uid),
            "atqa": "{:02x}:{:02x}".format(0x03, 0x44),  # Only with iso-a
            "sak": "{:02x}".format(0x20),  # Only with iso-a
        })

        # Beep card reader and set LED to green.
        cardconnection.transmit(bytes=[0xFF, 0x00, 0x40, 0x34, 0x04, 0x02, 0x02, 0x01, 0x01])
    except IndexError as e:
        traceback.print_exc()
        print_console(f"Invalid card scan - {e}", level="error")
        notify_toast(title="Invalid card scan", message=f"{e}")


def process_classic_a_response(cardconnection, rdata, sw1, sw2):
    try:
        sak = rdata[6]
        uidlen = rdata[7]
        atqa = rdata[4:6]
        uid = rdata[8:(8 + uidlen)]

        send_nfc_tag({
            "type": "iso-a",
            "uid": ":".join("{:02x}".format(x) for x in uid),
            "atqa": "{:02x}:{:02x}".format(atqa[0], atqa[1]),  # Only with iso-a
            "sak": "{:02x}".format(sak),  # Only with iso-a
        })

        # Beep card reader and set LED to green.
        cardconnection.transmit(bytes=[0xFF, 0x00, 0x40, 0x34, 0x04, 0x02, 0x02, 0x01, 0x01])
    except IndexError as e:
        traceback.print_exc()
        print_console(f"Invalid card scan, please retry - {e}", level="error")
        notify_toast(title="Invalid card scan", message=f"Please retry the last card scan - {e}")


def process_classic_b_response(cardconnection, atr):
    try:
        uidlen = 4
        uid = atr[5:(5 + uidlen)]

        send_nfc_tag({
            "type": "iso-b",
            "uid": ":".join("{:02x}".format(x) for x in uid)
        })

        # Beep card reader and set LED to green.
        cardconnection.transmit(bytes=[0xFF, 0x00, 0x40, 0x34, 0x04, 0x02, 0x02, 0x01, 0x01])
    except IndexError as e:
        traceback.print_exc()
        print_console(f"Invalid card scan, please retry - {e}", level="error")
        notify_toast(title="Invalid card scan", message=f"Please retry the last card scan - {e}")


class RfidReaderObserver(ReaderObserver):
    def update(self, observable, actions):
        (added, removed) = actions
        for reader in added:
            print_console(f"Card reader found: {reader}", level="warning")
            notify_toast(title="Card reader connected", message=f"{reader} is now available")
        for reader in removed:
            print_console(f"Card reader removed: {reader}", level="warning")
            notify_toast(title="Card reader disconnected", message=f"{reader} is no longer available")
        if not smartcard.System.readers():
            print_console(f"No readers found.")


class RfidCardObserver(CardObserver):
    def update(self, observable, actions):
        (added, removed) = actions
        if added:
            for card in added:
                conn = card.createConnection()
                try:
                    conn.connect()
                except CardConnectionException as e:
                    traceback.print_exc()
                    print_console(f"Could not connect to card, please retry - {e}", level="error")
                    notify_toast(title="Invalid card scan", message=f"Please retry the last card scan\n{e.__class__.__name__}: {e}")
                    continue

                # Set card reader LED to orange.
                conn.transmit(bytes=[0xFF, 0x00, 0x40, 0x3C, 0x04, 0x01, 0x01, 0x01, 0x00])
                # If we didn't turn the buzzer off yet, disable it.
                conn.transmit(bytes=[0xFF, 0x00, 0x52, 0x00, 0x00])

                # Ask the card for its ATR
                try:
                    atr = conn.getATR()
                except CardConnectionException as e:
                    traceback.print_exc()
                    print_console(f"Invalid card scan, please retry - {e}", level="error")
                    notify_toast(title="Invalid card scan", message=f"Please retry the last card scan\n{e.__class__.__name__}: {e}")
                    continue

                atr_str = "".join("{:02x}".format(x) for x in atr)
                if atr_str == "3b8180018080":
                    # DESFire card, retrieve data in a different way
                    # Keep retrying until success, as it can be the card was improperly shut down,
                    # or the connection is bad, which can make these multiple commands fail pretty easily.
                    # References:
                    # - https://stackoverflow.com/questions/29819356/apdu-for-getting-uid-from-mifare-desfire
                    # - https://stackoverflow.com/questions/40101316/whats-the-difference-between-desfire-and-desfire-ev1-cards
                    # - https://stackoverflow.com/questions/15967255/how-to-get-sak-to-identify-smart-card-type-using-java
                    # - https://smartcard-atr.apdu.fr/parse?ATR=3b8180018080
                    scan_success = False
                    while not scan_success:
                        version_info = []
                        try:
                            rdata, s1, s2 = conn.transmit(bytes=[0x90, 0x60, 0x00, 0x00, 0x00])
                            if s1 != 0x91 or s2 != 0xAF:  # If not MORE_DATA
                                raise ValueError("Failed on initial getVersion")
                            version_info.extend(rdata)
                            rdata, s1, s2 = conn.transmit(bytes=[0x90, 0xAF, 0x00, 0x00, 0x00])
                            if s1 != 0x91 or s2 != 0xAF:  # If not MORE_DATA
                                raise ValueError("Failed on second getVersion")
                            version_info.extend(rdata)
                            rdata, s1, s2 = conn.transmit(bytes=[0x90, 0xAF, 0x00, 0x00, 0x00])
                            if s1 != 0x91 or s2 != 0x00:  # If not CMD_SUCCESS
                                raise ValueError("Failed on final getVersion")
                            version_info.extend(rdata)
                            process_desfire_response(conn, version_info)
                            scan_success = True
                        except ValueError as e:
                            logging.warning(f"DESFire getVersion fail, retrying: {e}")
                        except IndexError as e:
                            traceback.print_exc()
                            print_console(f"Invalid card scan, please retry - {e}", level="error")
                            notify_toast(title="Invalid card scan", message=f"Please retry the last card scan\n{e.__class__.__name__}: {e}")
                        except CardConnectionException as e:
                            scan_success = True
                            traceback.print_exc()
                            print_console(f"Invalid card scan, please retry - {e}", level="error")
                            notify_toast(title="Invalid card scan", message=f"Please retry the last card scan\n{e.__class__.__name__}: {e}")
                elif atr[0] == 0x3b and atr[4] == 0x80:
                    # MiFare Classic type A
                    rdata, s1, s2 = conn.transmit(bytes=[0xFF, 0x00, 0x00, 0x00, 0x04, 0xD4, 0x4A, 0x01, 0x00])
                    process_classic_a_response(conn, rdata, s1, s2)
                elif atr[0] == 0x3b and atr[4] == 0x50:
                    # MiFare Classic type B
                    process_classic_b_response(conn, atr)
                else:
                    print_console(f"A card was scanned, but the type was unknown. (ATR 0x{atr_str[:12]})", level="error")
                    notify_toast(title="Unknown card", message="A card was scanned, but the type was unknown.")
                conn.disconnect()


app = Flask(__name__)
app.debug = False
app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
sock = Sock(app)


socket_clients = []


@sock.route('/')
def websocket(ws):
    global socket_clients
    socket_clients.append(ws)
    print_console(f"New connection: {request.remote_addr}", level="info")
    try:
        while True:
            time.sleep(5)
            if not ws.connected:
                break
    except:
        pass
    socket_clients.remove(ws)
    print_console(f"Client disconnected: {request.remote_addr}", level="info")


def send_nfc_tag(card):
    if DO_KIOSK_XSET:
        Popen(["/bin/su", "kiosk", "-s", "/bin/bash", "-c", "/usr/bin/xset -display :0 dpms force on"])

    if card['type'] == "iso-a":
        print_console(f"Scanned: ISO Type A -- UID<{card['uid']}>  ATQA<{card['atqa']}>  SAK<{card['sak']}>", level="info")
    elif card['type'] == "iso-4":
        print_console(f"Scanned: ISO DESFire -- UID<{card['uid']}>  ATQA<{card['atqa']}>  SAK<{card['sak']}>", level="info")
    elif card['type'] == "iso-b":
        print_console(f"Scanned: ISO Type B -- UID<{card['uid']}>", level="info")
    else:
        print_console(f"Scanned: UNKNOWN -- {card}", level="warning")

    global socket_clients
    for socket in socket_clients:
        socket.send(json.dumps(card))


def run_gui():
    global gui_app
    from gui.controller import JulianaApp
    gui_app = JulianaApp(False)
    gui_app.MainLoop()


if __name__ == '__main__':
    logging.info(f"{APP_NAME} v{APP_VERSION} (By {APP_AUTHOR})")
    logging.info(f"Support: {APP_SUPPORT}\n")

    if "-h" in sys.argv:
        logging.info(f"Usage: {sys.argv[0]} [-c] [-h] [-k]")
        logging.info("----------------------------")
        logging.info("-c   | Run in CLI mode, no GUI or tray icon")
        logging.info("-h   | Show this help and exit")
        logging.info("-k   | Run in Inter-Actief cookie corner kiosk mode (unsupported)")
        sys.exit(0)

    HAS_GUI = "-c" not in sys.argv
    DO_KIOSK_XSET = "-k" in sys.argv

    if HAS_GUI:
        gui_thread = threading.Thread(target=run_gui)
        gui_thread.daemon = True
        gui_thread.start()

        while gui_app is None:
            time.sleep(0.01)

    readers = smartcard.System.readers()
    if not readers:
        print_console("No readers found.", level="warning")
        notify_toast(title="No card reader", message="There are no card readers available")
    else:
        print_console(f"Found {len(readers)} card readers:", level="info")
        for reader in readers:
            print_console(f"  - {reader}", level="info")
            notify_toast(title="Card reader connected", message=f"{reader} is now available")

    reader_monitor = ReaderMonitor()
    reader_observer = RfidReaderObserver()
    reader_monitor.addObserver(reader_observer)
    card_monitor = CardMonitor()
    card_observer = RfidCardObserver()
    card_monitor.addObserver(card_observer)
    app.run(port=3000)
