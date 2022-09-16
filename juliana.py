#!/usr/bin/python3 -u

import os
import sys
import json
import time
import random
import string
import logging
import threading
import traceback

from datetime import datetime
from subprocess import Popen
from typing import Union

import nfc
import nfc.tag.tt1
import nfc.tag.tt2
import nfc.tag.tt3
import nfc.tag.tt4

from flask import Flask, request
from flask_cors import CORS
from flask_sock import Sock

from tendo.singleton import SingleInstance, SingleInstanceException
from simple_websocket.ws import ConnectionClosed


APP_VERSION = "3.2"
APP_NAME = "JulianaNFC"
APP_AUTHOR = "Kevin Alberts, I.C.T.S.V. Inter-/Actief/"
APP_SUPPORT = "www@inter-actief.net"
APP_LINK = "https://github.com/Inter-Actief/JulianaNFC_Python"


DEBUG = False
HAS_GUI = False
DO_KIOSK_XSET = False
gui_app = None

# RFID type targets to listen for, see https://nfcpy.readthedocs.io/en/latest/modules/clf.html#contactless-frontend
RFID_TARGETS = ['106A', '106B', '212F']

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
        if gui_app is not None:
            gui_app.add_message(f"[{datetime.now():%H:%M:%S}] {message}")


def resource_path(relative):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), relative)


def notify_toast(title, message, app_icon="resources/main.ico", force=False):
    if HAS_GUI or force:
        from notifypy import Notify
        notification = Notify()
        notification.application_name = f"{APP_NAME} {APP_VERSION}"
        notification.title = title
        notification.message = message
        notification.icon = resource_path(app_icon)
        notification.send(block=False)


class RfidCardManager(threading.Thread):
    """Reads card information when a card is sensed. Stops when the reader is not available."""
    def __init__(self, device: nfc.clf.device.Device):
        super(RfidCardManager, self).__init__()
        self.device = device
        self.log = logging.getLogger(self.__class__.__name__)
        self.running = True
        self.daemon = True
        self.just_started = True
        self.last_scanned = None

    def run(self):
        self.log.debug(f"Started RFID card manager for device {self.device}. Waiting for a card...")
        while self.running:
            tag = clf.connect(rdwr={
                'targets': RFID_TARGETS,
                'on-connect': self.on_connect,
                'on-release': self.on_release
            })
            self.log.debug(f"Tag removed: {tag}")

    @staticmethod
    def handle_card(card: nfc.tag.Tag):
        if isinstance(card, nfc.tag.tt1.Type1Tag):
            # Unsupported
            print_console(f"A card was scanned, but the type is unsupported. "
                          f"(Type {card.type}, ID: {card.identifier.hex()})", level="error")
            notify_toast(title="Unsupported card", message="A card was scanned, but the type is not supported.")
        elif isinstance(card, nfc.tag.tt2.Type2Tag):
            RfidCardManager.handle_card_type_a(card)
        elif isinstance(card, nfc.tag.tt3.Type3Tag):
            # Unsupported
            print_console(f"A card was scanned, but the type is unsupported. "
                          f"(Type {card.type}, ID: {card.identifier.hex()})", level="error")
            notify_toast(title="Unsupported card", message="A card was scanned, but the type is not supported.")
        elif isinstance(card, nfc.tag.tt4.Type4ATag):
            RfidCardManager.handle_card_type_a(card)
        elif isinstance(card, nfc.tag.tt4.Type4BTag):
            RfidCardManager.handle_card_type_4b(card)
            pass  # Unimplemented
        else:
            # Unknown
            print_console(f"A card was scanned, but the type is unknown. "
                          f"(Type {card.type}, ID: {card.identifier.hex()})", level="error")
            notify_toast(title="Unknown card", message="A card was scanned, but the type is not supported.")

    @staticmethod
    def handle_card_type_a(card: Union[nfc.tag.tt2.Type2Tag, nfc.tag.tt4.Type4ATag]):
        logging.debug(f"Scanned Type 2 or Type 4A card: {card}")

        # If the UID is 4 bytes long, and the first byte is 0x08, the card is using a Random-ID, so deny it.
        # See section 2.1.1: https://www.nxp.com/docs/en/application-note/AN10927.pdf
        if len(card.identifier) == 4 and card.identifier[0] == 0x08:
            print_console(f"A Type A card was scanned, but it is using a random UID. "
                          f"(Type {card.type}, ID: {card.identifier.hex()})", level="error")
            notify_toast(title="Unsupported card", message="The card that was scanned has a randomized ID, "
                                                           "so it cannot be used.")
        # If the UID is 4 bytes long, and the first byte is xF (x can be any number),
        # the card is using a fixed but non-unique ID, so deny it.
        # See section 2.1.2: https://www.nxp.com/docs/en/application-note/AN10927.pdf
        elif len(card.identifier) == 4 and (card.identifier[0] & 0x0F) == 0x0F:
            print_console(f"A Type A card was scanned, but it is using a non-unique ID. "
                          f"(Type {card.type}, ID: {card.identifier.hex()})", level="error")
            notify_toast(title="Unsupported card", message="The card that was scanned has a non-unique ID, "
                                                           "so it cannot be used.")
        else:
            send_nfc_tag({
                "type": "iso-a",
                "uid": ":".join("{:02x}".format(b) for b in card.identifier),
                "atqa": ":".join("{:02x}".format(b) for b in card.target.sens_res[::-1]),  # Only with iso-a
                "sak": ":".join("{:02x}".format(b) for b in card.target.sel_res),  # Only with iso-a
            })

    @staticmethod
    def handle_card_type_4b(card: nfc.tag.tt4.Type4BTag):
        logging.debug(f"Scanned Type 4B card: {card} {card.identifier.hex()}")
        send_nfc_tag({
            "type": "iso-b",
            "uid": ":".join("{:02x}".format(b) for b in card.identifier),
        })

    @staticmethod
    def on_connect(tag):
        # Read the tag
        RfidCardManager.handle_card(tag)
        # Resume the main thread loop only after the card has been removed from the reader
        return True

    @staticmethod
    def on_release(tag):
        # Loop while card is present
        while True:
            time.sleep(0.3)
            if not clf.sense(*[nfc.clf.RemoteTarget(target) for target in RFID_TARGETS]):
                break
        logging.debug(f"Tag released: {tag}. Class: {tag.__class__}")


class RfidReaderManager(threading.Thread):
    """Opens and closes reader connections when a reader is disconnected / connected from the PC"""
    def __init__(self, clf: nfc.ContactlessFrontend, target: str):
        super(RfidReaderManager, self).__init__()
        self.clf = clf
        self.target = target
        self.log = logging.getLogger(self.__class__.__name__)
        self.running = True
        self.daemon = True
        self.just_started = True
        self.card_manager = None

    def run(self):
        self.log.debug("Started RFID reader manager.")
        while self.running:
            # If a reader is opened, do nothing. Else, try to open a new reader.
            if self.clf.device:
                time.sleep(3)
            else:
                self.clf.close()
                try:
                    if self.clf.open(self.target):
                        print_console(f"Found NFC card reader: {self.clf.device}", level="info")
                        notify_toast(title="Card reader connected", message=f"{self.clf.device} is now available")
                        if self.card_manager is not None:
                            self.card_manager.running = False
                        self.card_manager = RfidCardManager(self.clf.device)
                        self.card_manager.start()
                    else:
                        if self.just_started:
                            self.just_started = False
                            print_console("No readers found.", level="warning")
                            notify_toast(title="No card reader", message="There are no card readers available")
                        time.sleep(3)
                except Exception as e:
                    error = traceback.format_exc(e)
                    print_console(f"Could not open card reader: {e}\n{error}", level="error")
                    notify_toast(title="Card reader error",
                                 message=f"Could not open card reader. See info window or console for details.")
                    sys.exit(2)


app = Flask(__name__)
app.debug = False
app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
sock = Sock(app)
cors = CORS(app, supports_credentials=True)


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
        print_console(f"Scanned: ISO Type A -- UID<{card['uid']}>  ATQA<{card['atqa']}>  SAK<{card['sak']}>",
                      level="info")
    elif card['type'] == "iso-4":
        print_console(f"Scanned: ISO DESFire -- UID<{card['uid']}>  ATQA<{card['atqa']}>  SAK<{card['sak']}>",
                      level="info")
    elif card['type'] == "iso-b":
        print_console(f"Scanned: ISO Type B -- UID<{card['uid']}>", level="info")
    else:
        print_console(f"Scanned: UNKNOWN -- {card}", level="warning")

    global socket_clients
    for socket in socket_clients:
        try:
            socket.send(json.dumps(card))
        except ConnectionClosed:
            pass


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

    try:
        one_instance_check = SingleInstance()
    except SingleInstanceException:
        print_console(f"JulianaNFC is already running, please close it before starting again", level="error")
        notify_toast(title="JulianaNFC already running",
                     message="JulianaNFC is already running, please close it before starting again!",
                     force=True)
        sys.exit(1)

    try:
        if HAS_GUI:
            gui_thread = threading.Thread(target=run_gui)
            gui_thread.daemon = True
            gui_thread.start()

            while gui_app is None:
                time.sleep(0.01)

        clf = nfc.ContactlessFrontend()
        reader_manager = RfidReaderManager(clf=clf, target='usb')
        reader_manager.start()

        app.run(port=3000)
    except Exception as e:
        error = traceback.format_exc(e)
        print_console(f"Generic exception occurred: {e}\n{error}", level="error")
        notify_toast(title="Juliana has crashed",
                     message=f"A general error has occurred. See info window or console for details.")
        sys.exit(2)

