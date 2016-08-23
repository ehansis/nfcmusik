# nfcmusik

**Goal:** build a simple mp3 player that is usable for toddlers, based on a raspberry pi.

Music is started via placing an NFC token on a sensor.
That's all the user interface there is.


## Requirements

### Base OS

Built and tested with Raspian Jessie (2016-05-27).

### System packages

Install these via `apt-get install <package>`, after doing an `apt-get upgrade`
* (none)

Optional:
* vim
* ipython

### Python packages

Install these with `pip install <package>`
* flask


## Usage

Clone into a directory of your choice on the RasPi. Run `controller.py` to start. 
See comment in `controller.py` for how to autostart on reboot.

