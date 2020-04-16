import binascii
import glob
import hashlib
import json
import logging
import time
from multiprocessing import Process, Lock, Manager
from os import path

import pygame
import vlc
from flask import Flask, render_template, request

import settings
import streams
import util
from rfid import RFID

logger = logging.getLogger(__name__)

"""

Main controller, runs in an infinite loop. 

Reads and acts on NFC codes, supplies web interface for tag management.
Web interface is at http://<raspi IP or host name>:5000

Autostart: 'crontab -e', then add line
@reboot cd <project directory> && python -u controller.py 2>&1 >> /home/pi/tmp/nfcmusik.log.txt &

"""

# control bytes for NFC payload
CONTROL_BYTES = dict(MUSIC_FILE=b"\x11", VLC_PLAYER=b"\x21")

# global debug output flag
DEBUG = False

# VLC playback commands (names must be unique!)
VLC_PAUSE = "pause"
VLC_PLAY = "play"
VLC_ACTIONS = [
    dict(name="Pause", action=VLC_PAUSE),
    dict(
        name="NDR Mikado, neueste Folge",
        action=VLC_PLAY,
        url_func=streams.ndr_mikado_latest,
    ),
    dict(
        name="BR Klaro - Nachrichten für Kinder, neueste Folge",
        action=VLC_PLAY,
        url_func=streams.br_klaro_latest,
    ),
    dict(
        name="BR Betthupferl, neueste Folge",
        action=VLC_PLAY,
        url_func=streams.br_betthupferl,
    ),
    dict(
        name="BR Geschichten für Kinder, neueste Folge",
        action=VLC_PLAY,
        url_func=streams.br_geschichten_fuer_kinder,
    ),
    dict(
        name="BR Radio Mikro, neueste Folge",
        action=VLC_PLAY,
        url_func=streams.br_radio_mikro,
    ),
    dict(
        name="BR Do Re Mikro, neueste Folge",
        action=VLC_PLAY,
        url_func=streams.br_do_re_mikro,
    ),
    dict(
        name="Deutschlandradio Kultur Kinderhörspiel, neueste Folge",
        action=VLC_PLAY,
        url_func=streams.dr_kinderhoerspiel,
    ),
]


def vlc_action_hash(action_id):
    """
    Get hash of VLC action, replace first byte with a control byte for VLC actions.
    """
    m = hashlib.md5()
    m.update(action_id.encode('utf8'))
    return CONTROL_BYTES["VLC_PLAYER"] + m.digest()[1:]


# populate hashes for all VLC actions
for a_ in VLC_ACTIONS:
    a_["hash"] = vlc_action_hash(a_["name"])  # noqa

# build dict, keyed by hashes
vlc_actions_dict = {a_["hash"]: a_ for a_ in VLC_ACTIONS}


class RFIDHandler(object):
    """
    RFID handler
    """

    def __init__(self):
        # flag to stop polling
        self.do_stop = False

        # mutex for RFID access
        self.mutex = Lock()

        # manager for interprocess data sharing (polling process writes uid/data)
        self.manager = Manager()

        # current tag uid
        self.uid = self.manager.list(range(5))

        # current tag data - 16 bytes
        self.data = self.manager.list(range(16))

        # music files dictionary
        self.music_files_dict = self.manager.dict()

        # have we shut off WiFi already?
        self.is_wlan_off = False

        # NFC memory page to use for reading/writing
        self.page = 10

        # polling cycle time (seconds)
        self.sleep = 0.5

        # music playing status
        self.current_track = None

        # last played music file
        self.previous_track = None

        # VLC player instance
        self.vlc_instance = vlc.Instance("--input-repeat=-1", "--aout=alsa")
        self.vlc_player = self.vlc_instance.media_player_new()

    def poll_loop(self):
        """
        Poll for presence of tag, read data, until stop() is called.
        """

        # initialize music mixer
        pygame.mixer.init()

        # set default volume
        util.set_volume(settings.DEFAULT_VOLUME)

        while not self.do_stop:
            with self.mutex:

                # initialize tag state
                self.uid[0] = None
                self.data[0] = None

                # always create a new RFID interface instance, to clear any errors from previous operations
                rdr = RFID()

                # check for presence of tag
                err, _ = rdr.request()

                if not err:
                    logger.debug("RFIDHandler poll_loop: Tag is present")

                    # tag is present, get UID
                    err, uid = rdr.anticoll()

                    if not err:
                        logger.debug(f"RFIDHandler poll_loop: Read UID: {uid}")

                        # read data
                        err, data = rdr.read(self.page)

                        if not err:
                            logger.debug(
                                f"RFIDHandler poll_loop: Read tag data: {data}"
                            )

                            # all good, store data to shared mem
                            for i in range(5):
                                self.uid[i] = uid[i]
                            for i in range(16):
                                self.data[i] = data[i]

                        else:
                            logger.debug(
                                "RFIDHandler poll_loop: Error returned from read()"
                            )

                    else:
                        logger.debug(
                            "RFIDHandler poll_loop: Error returned from anticoll()"
                        )

                # clean up
                rdr.cleanup()

                # act on data
                self.action()

            # wait a bit (this is in while loop, NOT in mutex env)
            time.sleep(self.sleep)

    def write(self, data):
        """
        Write a 16-byte string of data to the tag
        """

        if len(data) != 16:
            logger.debug(f"Illegal data length, expected 16, got {len(data)}")
            return False

        with self.mutex:
            rdr = RFID()

            success = False

            # check for presence of tag
            err, _ = rdr.request()

            if not err:
                logger.debug("RFIDHandler write: Tag is present")

                # tag is present, get UID
                err, uid = rdr.anticoll()

                if not err:
                    logger.debug("RFIDHandler write: Read UID: " + str(uid))

                    # write data: RFID lib writes 16 bytes at a time, but for NTAG213
                    # only the first four are actually written
                    err = False
                    for i in range(4):
                        page = self.page + i
                        page_data = data[4 * i : 4 * i + 4] + b"\x00" * 12

                        # read data once (necessary for successful writing?)
                        err_read, _ = rdr.read(page)

                        if err:
                            logger.debug(
                                "Error signaled on reading page {:d} before writing".format(
                                    page
                                )
                            )

                        # write data
                        err |= rdr.write(page, page_data)

                        if err:
                            logger.debug(
                                f"Error signaled on writing page {page:d} with data {page_data:s}"
                            )

                    if not err:
                        logger.debug("RFIDHandler write: successfully wrote tag data")

                        success = True

                    else:
                        logger.debug("RFIDHandler write: Error returned from write()")

                else:
                    logger.debug("RFIDHandler write: Error returned from anticoll()")

            # clean up
            rdr.cleanup()

            return success

    def get_data(self):
        """
        Get current tag data as binary string
        """
        with self.mutex:
            data = list(self.data)
        if data[0] is not None:
            return bytes(data)
        else:
            return None

    def get_uid(self):
        """
        Get current tag UID
        """
        with self.mutex:
            uid = list(self.uid)
        if uid[0] is not None:
            return bytes(uid)
        else:
            return None

    def set_music_files_dict(self, mfd):
        """
        Set dictionary of file hashes and music files
        """
        with self.mutex:
            for k, v in mfd.items():
                self.music_files_dict[k] = v

    def stop_polling(self):
        """
        Stop polling loop
        """
        self.do_stop = True

    def action(self):
        """
        Act on NFC data - call this from within a mutex lock
        """

        # check if we have valid data
        if self.data[0] is not None:
            bin_data = bytes(self.data)

            if bin_data[:1] == CONTROL_BYTES["MUSIC_FILE"]:
                self.vlc_player.pause()

                if bin_data in self.music_files_dict:
                    file_name = self.music_files_dict[bin_data]
                    file_path = path.join(settings.MUSIC_ROOT, file_name)

                    if file_name != self.current_track:
                        if pygame.mixer.music.get_busy():
                            pygame.mixer.music.stop()

                        if path.exists(file_path):
                            logger.info(f"Playing music file: {file_path}")
                            self.current_track = file_name
                            self.previous_track = file_name
                            pygame.mixer.music.load(file_path)
                            pygame.mixer.music.play()

                        else:
                            if not path.exists(file_path):
                                logger.debug(f"File not found: {file_path}")

            elif bin_data[:1] == CONTROL_BYTES["VLC_PLAYER"]:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                if bin_data in vlc_actions_dict:
                    action = vlc_actions_dict[bin_data]

                    if action["action"] == VLC_PLAY:
                        if action["name"] != self.current_track:
                            if action["name"] == self.previous_track:
                                # we are paused, unpause
                                self.current_track = self.previous_track
                                self.vlc_player.play()
                            else:
                                self.current_track = action["name"]
                                self.previous_track = action["name"]

                                # start playback of new track
                                url = action["url_func"]()
                                if url is None:
                                    logger.debug("Failed to get track URL")
                                else:
                                    media = self.vlc_instance.media_new(url)
                                    self.vlc_player.set_media(media)
                                    self.vlc_player.play()
                    elif action["action"] == VLC_PAUSE and self.current_track is not None:
                        self.current_track = None
                        self.vlc_player.pause()

                else:
                    logger.debug("Got VLC action control byte, but unknown name hash")
            else:
                logger.debug("Unknown control byte")


#
# Global objects
#

app = Flask(__name__)

# global dictionary of music file hashes and names
music_files_dict = dict()

# global RFID handler instance
rfid_handler = RFIDHandler()

# RFID handling process
rfid_polling_process = Process(target=rfid_handler.poll_loop)


#
# End global objects
#


def music_file_hash(file_name):
    """
    Get hash of music file name, replace first byte with a control byte for music playing.
    """
    m = hashlib.md5()
    m.update(file_name.encode("utf8"))
    return CONTROL_BYTES["MUSIC_FILE"] + m.digest()[1:]


@app.route("/json/musicfiles")
def music_files():
    """
    Get a list of music files and file identifier hashes as JSON; also refresh
    internal cache of music files and hashes.
    """
    global music_files_dict

    file_paths = sorted(glob.glob(path.join(settings.MUSIC_ROOT, "*")))

    out = []
    music_files_dict = dict()
    for file_path in file_paths:
        file_name = path.split(file_path)[1]
        file_hash = music_file_hash(file_name)
        out.append(
            dict(name=file_name, hash=binascii.b2a_hex(file_hash).decode("utf8"))
        )
        music_files_dict[file_hash] = file_name

    # set music files dict in RFID handler
    rfid_handler.set_music_files_dict(music_files_dict)

    return json.dumps(out)


@app.route("/json/vlcactions")
def vlc_actions():
    """
    Get a list of VLC actions identifier hashes as JSON; also refresh
    internal cache of VLC actions and hashes.
    """
    actions = [
        dict(name=a["name"], hash=binascii.b2a_hex(a["hash"]).decode("utf8"))
        for a in VLC_ACTIONS
    ]
    return json.dumps(actions)


@app.route("/json/readnfc")
def read_nfc():
    """
    Get current status of NFC tag
    """
    global music_files_dict

    # get current NFC uid and data

    uid = rfid_handler.get_uid()
    if uid is None:
        hex_uid = b"none"
    else:
        hex_uid = binascii.b2a_hex(uid)

    data = rfid_handler.get_data()
    if data is None:
        hex_data = b"none"
        description = "No tag present"
    else:
        hex_data = binascii.b2a_hex(data)

        description = "Unknown control byte or tag empty"
        if data[:1] == CONTROL_BYTES["MUSIC_FILE"]:
            if data in music_files_dict:
                description = "Play music file " + music_files_dict[data]
            else:
                description = "Play a music file not currently present on the device"
        elif data[:1] == CONTROL_BYTES["VLC_PLAYER"]:
            action = vlc_actions_dict[data]
            description = "VLC: " + action["name"]

    # output container
    out = dict(
        uid=hex_uid.decode("utf8"),
        data=hex_data.decode("utf8"),
        description=description,
    )

    return json.dumps(out)


@app.route("/actions/writenfc")
def write_nfc():
    """
    Write data to NFC tag

    Data is contained in get argument 'data'.
    """
    hex_data = request.args.get("data").encode("utf8")

    if hex_data is None:
        logger.error("No data argument given for writenfc endpoint")
        return

    # convert from hex to bytes
    data = binascii.a2b_hex(hex_data)

    if data[:1] == CONTROL_BYTES["MUSIC_FILE"]:
        if data not in music_files_dict:
            return json.dumps(dict(message="Unknown hash value!"))

        # write tag
        success = rfid_handler.write(data)

        if success:
            file_name = music_files_dict[data]
            return json.dumps(
                dict(message="Successfully wrote NFC tag for file: " + file_name)
            )
        else:
            return json.dumps(dict(message="Error writing NFC tag data " + str(hex_data)))

    elif data[:1] == CONTROL_BYTES["VLC_PLAYER"]:
        if data not in vlc_actions_dict:
            return json.dumps(dict(message="Unknown hash value!"))

        # write tag
        success = rfid_handler.write(data)

        if success:
            action_name = vlc_actions_dict[data]["name"]
            return json.dumps(
                dict(message="Successfully wrote NFC tag for VLC action: " + action_name)
            )
        else:
            return json.dumps(dict(message="Error writing NFC tag data " + str(hex_data)))

    else:
        # noinspection PyTypeChecker
        return json.dumps(
            dict(message="Unknown control byte: " + str(binascii.b2a_hex(data[:1])))
        )


@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":
    # start RFID polling
    rfid_polling_process.start()

    # initialize music files dict
    music_files()

    # run server
    app.run(host=settings.SERVER_HOST_MASK, port=settings.SERVER_PORT, threaded=True)
