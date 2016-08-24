import glob
from os import path
import json
import hashlib
import binascii
import signal
import sys
import time
from multiprocessing import Process, Lock, Manager
import pygame

from flask import Flask, render_template, request

import settings
import RFID
import util


"""

Main controller, runs in an infinite loop. 

Reads and acts on NFC codes, supplies web interface for tag management.
Web interface is at http://<raspi IP or host name>:5000

Autostart: 'crontab -e', then add line
@reboot cd <project directory> && python -u controller.py 2>&1 >> /home/pi/tmp/nfcmusik.log.txt &

"""




# control bytes for NFC payload
CONTROL_BYTES = dict(
    MUSIC_FILE='\x11',
)


# global debug output flag
DEBUG = False


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

        # NFC memory page to use for reading/writing
        self.page = 10

        # polling cycle time (seconds)
        self.sleep = 1.0

        # music playing status
        self.current_music = None

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

                # always create a new RFID interface instance, to clear any errors from
                # previous operations
                rdr = RFID.RFID()

                # check for presence of tag
                err, _ = rdr.request()

                if not err:
                    if DEBUG:
                        print "RFIDHandler poll_loop: Tag is present"

                    # tag is present, get UID
                    err, uid = rdr.anticoll()

                    if not err:
                        if DEBUG:
                            print "RFIDHandler poll_loop: Read UID: " + str(uid)

                        # read data
                        err, data = rdr.read(self.page)

                        if not err:
                            if DEBUG:
                                print "RFIDHandler poll_loop: Read tag data: " + str(data)

                            # all good, store data to shared mem
                            for i in range(5):
                                self.uid[i] = uid[i]
                            for i in range(16):
                                self.data[i] = data[i]

                        else:
                            if DEBUG:
                                print "RFIDHandler poll_loop: Error returned from read()"

                    else:
                        if DEBUG:
                            print "RFIDHandler poll_loop: Error returned from anticoll()"

                # clean up
                rdr.cleanup()

                # act on data
                self.action()

                # wait a bit
                time.sleep(self.sleep)

    def write(self, data):
        """
        Write a 16-byte string of data to the tag
        """

        if len(data) != 16:
            if DEBUG:
                print "Illegal data length, expected 16, got " + str(len(data))
            return False

        with self.mutex:

            rdr = RFID.RFID()

            success = False

            # check for presence of tag
            err, _ = rdr.request()

            if not err:
                if DEBUG:
                    print "RFIDHandler write: Tag is present"

                # tag is present, get UID
                err, uid = rdr.anticoll()

                if not err:
                    if DEBUG:
                        print "RFIDHandler write: Read UID: " + str(uid)

                    # write data: RFID lib writes 16 bytes at a time, but for NTAG213
                    # only the first four are actually written
                    err = False
                    for i in range(4):
                        page = self.page + i
                        page_data = [ord(c) for c in data[4 * i : 4 * i + 4]] + [0] * 12

                        # read data once (necessary for successful writing?)
                        err_read, _ = rdr.read(page)

                        if DEBUG and err:
                                print "Error signaled on reading page {:d} before writing".format(page)

                        # write data
                        err |= rdr.write(page, page_data)

                        if DEBUG and err:
                                print "Error signaled on writing page {:d} with data {:s}".format(page, str(page_data))

                    if not err:
                        if DEBUG:
                            print "RFIDHandler write: successfully wrote tag data"

                        success = True

                    else:
                        if DEBUG:
                            print "RFIDHandler write: Error returned from write()"

                else:
                    if DEBUG:
                        print "RFIDHandler write: Error returned from anticoll()"

            # clean up
            rdr.cleanup()

            return success

    def get_data(self):
        """
        Get current tag data as binary string
        """
        with self.mutex:
            data = list(self.data)
        if data[0] != None:
            return "".join([chr(c) for c in data])
        else:
            return None

    def get_uid(self):
        """
        Get current tag UID
        """
        with self.mutex:
            uid = list(self.uid)
        if uid[0] != None:
            return "".join([chr(c) for c in uid])
        else:
            return None

    def set_music_files_dict(self, mfd):
        """
        Set dictionary of file hashes and music files
        """
        with self.mutex:
            for k, v in mfd.iteritems():
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
            bin_data = "".join([chr(c) for c in self.data])

            if bin_data[0] == CONTROL_BYTES['MUSIC_FILE']:
                if bin_data in self.music_files_dict:
                    file_name = self.music_files_dict[bin_data]
                    file_path = path.join(settings.MUSIC_ROOT, file_name)

                    if file_name != self.current_music:

                        if path.exists(file_path):
                            print "RFIDHandler action: Playing music file " + file_path

                            # play music file
                            self.current_music = file_name
                            pygame.mixer.music.load(file_path)
                            pygame.mixer.music.play()

                        else:
                            if DEBUG:
                                print "RFIDHandler action: File not found " + file_path
                else:
                    if DEBUG:
                        print "RFIDHandler: gut music file control byte but unknown file hash"
            else:
                if DEBUG:
                    print "RFIDHandler action: Unknown control byte"
        else:
            if DEBUG:
                print "Resetting action status"

            self.current_music = None

            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()


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
    m.update(file_name)
    return CONTROL_BYTES['MUSIC_FILE'] + m.digest()[1:]


@app.route("/json/musicfiles")
def music_files():
    """
    Get a list of music files and file identifier hashes as JSON; also refresh 
    internal cache of music files and hashes.
    """
    global music_files_dict
    
    file_paths = sorted(glob.glob(path.join(settings.MUSIC_ROOT, '*')))

    out = []
    music_files_dict = dict()
    for file_path in file_paths:
        file_name = path.split(file_path)[1]
        file_hash = music_file_hash(file_name)
        out.append(dict(name=file_name,
                        hash=binascii.b2a_hex(file_hash)))
        music_files_dict[file_hash] = file_name

        # set music files dict in RFID handler
        rfid_handler.set_music_files_dict(music_files_dict)

    return json.dumps(out)


@app.route("/json/readnfc")
def read_nfc():
    """
    Get current status of NFC tag
    """
    global music_files_dict

    # get current NFC uid and data

    uid = rfid_handler.get_uid()
    if uid is None:
        hex_uid = "none"
    else:
        hex_uid = binascii.b2a_hex(uid)

    data = rfid_handler.get_data()
    if data is None:
        hex_data = "none"
        description = "No tag present"
    else:
        hex_data = binascii.b2a_hex(data)

        description = 'Unknown control byte or tag empty'
        if data[0] == CONTROL_BYTES['MUSIC_FILE']:
            if data in music_files_dict:
                description = 'Play music file ' + music_files_dict[data]
            else:
                description = 'Play a music file not currently present on the device'

    # output container
    out = dict(uid=hex_uid,
               data=hex_data,
               description=description)

    return json.dumps(out)


@app.route("/actions/writenfc")
def write_nfc():
    """
    Write data to NFC tag

    Data is contained in get argument 'data'.
    """
    hex_data = request.args.get('data')

    if hex_data is None:
        print ("Error: no data argument given for writenfc endpoint")
        return

    # convert from hex to bytes
    data = binascii.a2b_hex(hex_data)

    if data[0] == CONTROL_BYTES['MUSIC_FILE']:
        if data not in music_files_dict:
            return json.dumps(dict(message="Unknown hash value!"))

        # write tag
        success = rfid_handler.write(data)

        if success:
            file_name = music_files_dict[data]
            return json.dumps(dict(message="Successfully wrote NFC tag for file: " + file_name))
        else:
            return json.dumps(dict(message="Error writing NFC tag data " + hex_data))

    else:
        return json.dumps(dict(message='Unknown control byte: ' + binascii.b2a_hex(data[0])))


@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":

    # start RFID polling
    rfid_polling_process.start()

    # initialize music files dict
    music_files()

    # run server
    app.run(host=settings.SERVER_HOST_MASK,
            threaded=True)

