# nfcmusik

**Goal:** build a simple mp3 player that is usable for toddlers, based on a raspberry pi.

Music is started via placing an NFC token on a sensor.
That's all the user interface there is.


## Requirements

### Base OS

Built and tested with Raspian Jessie (2016-05-27).

Enable the SPI interface using `sudo raspi-config`, then go to `Advanced Options` and enable SPI.

### System packages

Install these via `sudo apt-get install <package>`, after doing `sudo apt-get upgrade`
* python-dev (required for building SPI driver)

Optional:
* vim
* ipython

### Python packages

Install these with `pip install <package>`
* flask


## Integrated third-party code

The **RFID interface** (`RFID.py`) is based on https://github.com/ondryaso/pi-rc522, commit 
`6f5add08df29940bac15d3e9d98763fcc212ecc7`, with custom modifications.

The **SPI interface** code (folder `SPI-Py`) was cloned from https://github.com/mab5vot9us9a/SPI-Py, 
commit `3d537a7e40ae1a7035b147acf08a73c9e31027ea`, with no further modifications.

Build the SPI interface driver as follows:
```
cd SPI-Py
python setup.py build
sudo python setup.py install
rm -rv build
```


## NFC Tags

This project was built and tested with NXP NTAG213 tags. Contrary to the examples
and default usage in `RFID.py`, these do NOT require authentication
to be read or written. They also use 4-byte pages instead of 16-byte ones.
`read`s return 4 pages (16 bytes) at a time, but writes write 4 bytes only.
`RFID.py` can read 16 bytes fine, writes must happen with 16 bytes of data
of which only the first 4 are actually written.

*ToDo*: Fix `RFID.py` to correctly handle 4-byte writes..


## Usage

Copy music files to RasPi SD Card, adapt `settings.py` to point to correct `MUSIC_ROOT`
(this can be done via `scp` or by plugging the SD card into your PC/Mac).

Clone into a directory of your choice on the RasPi. Run `controller.py` to start. 
See comment in `controller.py` for how to autostart on reboot.

Open http://<RasPi IP or host name>:5000 to access NFC tag management.
Place tag on reader, click 'write to tag' besides one of the listed music files
to assign the file to the tag.


