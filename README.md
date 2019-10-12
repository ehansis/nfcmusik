# nfcmusik

**Goal:** build a simple mp3 player that a toddler can use, based on a raspberry pi.

A song is started by placing an NFC token on a sensor. Removing the token stops the music.
That's all the user interface there is.

In my setup, the RasPi is hidden in a wooden box, that also contains a pair of tiny USB speakers.
The NFC sensor is screwed to the inside of the lid. 
As tokens I use plastic poker chips. Each token plays one specific song.
On one side I stick an NFC tag, on the other I draw a little icon
symbolizing the song to be played by this token.

![Image of the player, box closed](images/nfcmusik_box_1.jpg)

![Image of the player, box opened](images/nfcmusik_box_2.jpg)


The music box is configured via a web interface, in which you can assign a song to 
a specific NFC tag. 

![Screenshot of the UI with an NFC tag present](images/nfcmusik_UI_2.png)


## Shopping list

Here's what I bought to build the player (no, I'm in no way affiliated with Amazon...):
- [Neuftech Mifare RC522 RFC Reader](https://www.amazon.de/gp/product/B00QFDRPZY/)
- [Trust Leto 2.0 USB Speakers](https://www.amazon.de/gp/product/B00JRW0M32/)
- [20 NFC Tags Sticker NTAG213 Circus round 22mm 168Byte](https://www.amazon.de/gp/product/B00BTKAI7U/)
- Some USB power supply, plus a USB extension cable
- [Aukru 40x 20cm female-female jumper wire](https://www.amazon.de/gp/product/B00OL6JZ3C/) to wire the RFC reader to the RasPi
- [Raspberry Board Pi 3 Model B](https://www.amazon.de/gp/product/B01CCOXV34/)
- Some SD Card (16 GB)
- Some RasPi Case
- A wooden box, about the size of a shoe box, from a DIY store


## RasPi Setup

### WLAN access point

Configure the raspi to act as a WLAN access point on interface `wlan0`. 
See, for example, [this site](https://frillip.com/using-your-raspberry-pi-3-as-a-wifi-access-point-with-hostapd/) for instructions.
Note the static IP that you assign to the RasPi while configuring. This will be the address where
you can access the user interface (also see below).

The `wlan0` interface is automatically shut down 3 minutes after startup, to avoid unneccessary 'radiation' and
to reduce interference in the speakers. Refreshing the home page of the user interface resets
the shutdown timer. After the access point has shut down, you would need to re-boot the RasPi to 
reconnect (or connect to it via LAN).

### Base OS

The code was built and tested with Raspbian Jessie (2016-05-27).
Enable the SPI interface using `sudo raspi-config`, then go to `Advanced Options` and enable SPI.

Alternatively, you can also flash a [hypriot image](https://blog.hypriot.com) (Raspbian Buster including a working installation of docker) by use of the [hypriot flash](https://github.com/hypriot/flash) utility.
The configuration files used in this process are located under `setup/image`.
To use it to flash an sd card, just run

```
make flash
```

and follow the prompts.
No worries about enabling interfaces anymore. :)

### System packages

Install these via `sudo apt-get install <package>`, after doing `sudo apt-get upgrade`
* python-dev (required for building SPI driver)

Optional:
* vim
* ipython

### Python packages

Install these with `pip install <package>`
* flask


### SPI interface

Clone the [SPI-Py project](https://github.com/mab5vot9us9a/SPI-Py) into a directory `SPI-Py`.
Code is not included in this repo because SPI-Py is GPL (and I want my project license to be less restrictive).
The project was built and tested with commit `3d537a7e40ae1a7035b147acf08a73c9e31027ea` of SPI-Py.

Build the SPI interface driver as follows:
```
cd SPI-Py
python setup.py build
sudo python setup.py install
rm -rv build
```


## Integrated third-party code for RFID interface

The **RFID interface** (`RFID.py`) is based on [pi-rc522](https://github.com/ondryaso/pi-rc522), commit 
[`6f5add08df29940bac15d3e9d98763fcc212ecc7`](https://github.com/ondryaso/pi-rc522/tree/6f5add08df29940bac15d3e9d98763fcc212ecc7), with custom modifications.


## NFC Tags

This project was built and tested with NXP NTAG213 tags. Contrary to the examples
and default usage in `RFID.py`, these do NOT require authentication
to be read or written. They also use 4-byte pages instead of 16-byte ones.
`read`s return 4 pages (16 bytes) at a time, but writes write 4 bytes only.
`RFID.py` can read 16 bytes fine, writes must happen with 16 bytes of data
of which only the first 4 are actually written.

*ToDo*: Fix `RFID.py` to correctly handle 4-byte writes..


## NFC Reader

See [the pi-rc522 page](https://github.com/ondryaso/pi-rc522) for instructions on how to
connect the NFC reader to your RasPi. The RasPi pinout can be found [here](http://pinout.xyz/).


## Administration

Copy mp3 files to the RasPi SD Card, adapt `settings.py` to point to the correct `MUSIC_ROOT`
containing the mp3 files.
Copying can be done via `scp` or by plugging the SD card into your PC/Mac.
Music files contained in `MUSIC_ROOT` will be shown in the user interface and will
be playable by NFC tags.

Clone this git repo into a directory of your choice on the RasPi. Run `python controller.py` to start. 
See comment in `controller.py` for how to autostart on reboot.

Open `http://<RasPi IP or host name>:5000` to access NFC tag management.
Place tag on reader, click 'write to tag' besides one of the listed music files
to assign the file to the tag.


