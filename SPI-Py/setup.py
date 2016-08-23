#!/usr/bin/env python3
# coding=utf-8

from distutils.core import setup, Extension

module1 = Extension('spi', sources = ['spi.c'])

setup (
    name='SPI-Py',
    author='Louis Thiery (Original), Maurice Fahn (Adaptions)',
    url='https://github.com/mab5vot9us9a/SPI-Py',
    download_url='https://github.com/mab5vot9us9a/SPI-Py/archive/master.zip',
    version='1.0.1',
    description='SPI-Py: Hardware SPI as a C Extension for Python by Louis Thiery, adapted to work with MFRC522 under Raspbian Jessie by Maurice Fahn.',
    license='GPL-v2',
    platforms=['Linux'],
    ext_modules=[module1]
)
