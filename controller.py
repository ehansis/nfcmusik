import glob
from os import path
import json
import hashlib
import binascii

from flask import Flask, render_template, request

import settings


app = Flask(__name__)


# global dictionary of music file hashes and names
MUSIC_FILES = dict()


# control bytes for NFC payload
CONTROL_BYTES = dict(
    MUSIC_FILE='\x11',
)


def music_file_hash(file_name):
    """
    Get hash of music file name, prepended with a control byte for music playing.
    """
    m = hashlib.md5()
    m.update(file_name)
    return CONTROL_BYTES['MUSIC_FILE'] + m.digest()


@app.route("/json/musicfiles")
def music_files():
    """
    Get a list of music files and file identifier hashes as JSON; also refresh 
    internal cache of music files and hashes.
    """
    global MUSIC_FILES
    
    file_paths = sorted(glob.glob(path.join(settings.MUSIC_ROOT, '*')))

    out = []
    MUSIC_FILES = dict()
    for file_path in file_paths:
        file_name = path.split(file_path)[1]
        file_hash = music_file_hash(file_name)
        out.append(dict(name=file_name,
                        hash=binascii.b2a_hex(file_hash)))
        MUSIC_FILES[file_hash] = file_name

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
        if data not in MUSIC_FILES:
            return json.dumps(dict(message="Unknown hash value!"))

        file_name = MUSIC_FILES[data]

        return json.dumps(dict(message="Successfully wrote NFC tag for file: " + file_name))

    else:
        return json.dumps(dict(message='Unknown control byte: ' + binascii.b2a_hex(data[0])))


@app.route("/")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    app.run(host=settings.SERVER_HOST_MASK,
            threaded=True)

