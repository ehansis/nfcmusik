# coding=utf-8
from typing import List

import RPi.GPIO as GPIO
import spidev


class RFID:
    pin_rst = 22
    pin_ce = 0

    mode_idle = 0x00
    mode_auth = 0x0E
    mode_receive = 0x08
    mode_transmit = 0x04
    mode_transrec = 0x0C
    mode_reset = 0x0F
    mode_crc = 0x03

    auth_a = 0x60
    auth_b = 0x61

    act_read = 0x30
    act_write = 0xA0
    act_increment = 0xC1
    act_decrement = 0xC0
    act_restore = 0xC2
    act_transfer = 0xB0

    act_reqidl = 0x26
    act_reqall = 0x52
    act_anticl = 0x93
    act_select = 0x93
    act_end = 0x50

    length = 16

    # See §9 of https://www.nxp.com/docs/en/data-sheet/MFRC522.pdf for an overview over and
    # explanation of all registers.
    CommandReg = 0x01
    ComlEnReg = 0x02
    FIFODataReg = 0x09
    BitFramingReg = 0x0D
    ModeReg = 0x11
    TxControlReg = 0x14
    TxAutoReg = 0x15
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D

    authed = False

    def __init__(self, bus=0, device=0, speed=1000000, pin_rst=22, pin_ce=0):
        self.pin_rst = pin_rst
        self.pin_ce = pin_ce

        self.spi = spidev.SpiDev()
        self.spi.open(bus=bus, device=device)
        self.spi.max_speed_hz = speed

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin_rst, GPIO.OUT)
        GPIO.output(pin_rst, 1)
        if pin_ce != 0:
            GPIO.setup(pin_ce, GPIO.OUT)
            GPIO.output(pin_ce, 1)

        self.reset()
        self.dev_write(self.TModeReg, 0x8D)
        self.dev_write(self.TPrescalerReg, 0x3E)
        self.dev_write(self.TReloadRegL, 30)
        self.dev_write(self.TReloadRegH, 0)
        self.dev_write(self.TxAutoReg, 0x40)
        self.dev_write(self.ModeReg, 0x3D)
        self.set_antenna(True)

    def spi_transfer(self, address: int, *data: int) -> List[int]:
        if self.pin_ce != 0:
            GPIO.output(self.pin_ce, 0)
        ret = self.spi.xfer2([address] + list(data))
        if self.pin_ce != 0:
            GPIO.output(self.pin_ce, 1)
        return ret

    def dev_write(self, address, value):
        self.spi_transfer((address << 1) & 0x7E, value)

    def dev_read(self, address):
        return self.spi_transfer(((address << 1) & 0x7E) | 0x80, 0)[1]

    def set_bitmask(self, address, mask):
        current = self.dev_read(address)
        self.dev_write(address, current | mask)

    def clear_bitmask(self, address, mask):
        current = self.dev_read(address)
        self.dev_write(address, current & (~mask))

    def set_antenna(self, state):
        if state:
            current = self.dev_read(self.TxControlReg)
            if ~(current & 0x03):
                self.set_bitmask(self.TxControlReg, 0x03)
        else:
            self.clear_bitmask(self.TxControlReg, 0x03)

    def card_write(self, command, data):
        back_data = []
        back_length = 0
        error = False
        irq = 0x00
        irq_wait = 0x00

        if command == self.mode_auth:
            irq = 0x12
            irq_wait = 0x10
        if command == self.mode_transrec:
            irq = 0x77
            irq_wait = 0x30

        self.dev_write(self.ComlEnReg, irq | 0x80)
        self.clear_bitmask(0x04, 0x80)
        self.set_bitmask(0x0A, 0x80)
        self.dev_write(self.CommandReg, self.mode_idle)

        for i in range(len(data)):
            self.dev_write(self.FIFODataReg, data[i])

        self.dev_write(self.CommandReg, command)

        if command == self.mode_transrec:
            self.set_bitmask(0x0D, 0x80)

        i = 2000
        while True:
            n = self.dev_read(0x04)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & irq_wait)):
                break

        self.clear_bitmask(0x0D, 0x80)

        if i != 0:
            if (self.dev_read(0x06) & 0x1B) == 0x00:
                error = False

                if n & irq & 0x01:
                    error = True

                if command == self.mode_transrec:
                    n = self.dev_read(0x0A)
                    last_bits = self.dev_read(0x0C) & 0x07
                    if last_bits != 0:
                        back_length = (n - 1) * 8 + last_bits
                    else:
                        back_length = n * 8

                    if n == 0:
                        n = 1

                    if n > self.length:
                        n = self.length

                    for i in range(n):
                        back_data.append(self.dev_read(self.FIFODataReg))
            else:
                error = True

        return error, back_data, back_length

    def request(self, req_mode=0x26):
        """
        Requests for tag.
        Returns (False, None) if no tag is present, otherwise returns (True, tag type)
        """
        self.dev_write(self.BitFramingReg, 0x07)
        error, back_data, back_bits = self.card_write(self.mode_transrec, [req_mode, ])

        if error or (back_bits != 0x10):
            return True, None

        return False, back_bits

    def anticoll(self):
        """
        Anti-collision detection.
        Returns tuple of (error state, tag ID).
        """
        serial_number = []

        serial_number_check = 0

        self.dev_write(self.BitFramingReg, 0x00)
        serial_number.append(self.act_anticl)
        serial_number.append(0x20)

        (error, back_data, back_bits) = self.card_write(self.mode_transrec, serial_number)
        if not error:
            if len(back_data) == 5:
                for i in range(4):
                    serial_number_check = serial_number_check ^ back_data[i]

                if serial_number_check != back_data[4]:
                    error = True
            else:
                error = True

        return error, back_data

    def calculate_crc(self, data):
        self.clear_bitmask(0x05, 0x04)
        self.set_bitmask(0x0A, 0x80)

        for i in range(len(data)):
            self.dev_write(self.FIFODataReg, data[i])
        self.dev_write(self.CommandReg, self.mode_crc)

        i = 255
        while True:
            n = self.dev_read(0x05)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break

        ret_data = [self.dev_read(0x22), self.dev_read(0x21)]

        return ret_data

    def select_tag(self, uid):
        """
        Selects tag for further usage.
        uid -- list or tuple with four bytes tag ID
        Returns error state.
        """
        buf = [self.act_select, 0x70] + [uid[i] for i in range(5)]

        crc = self.calculate_crc(buf)
        buf.append(crc[0])
        buf.append(crc[1])

        (error, back_data, back_length) = self.card_write(self.mode_transrec, buf)

        if (not error) and (back_length == 0x18):
            return False
        else:
            return True

    def card_auth(self, auth_mode, block_address, key, uid):
        """
        Authenticates to use specified block address. Tag must be selected using select_tag(uid) before auth.
        auth_mode -- RFID.auth_a or RFID.auth_b
        key -- list or tuple with six bytes key
        uid -- list or tuple with four bytes tag ID
        Returns error state.
        """
        buf = [auth_mode, block_address] + [key[i] for i in range(len(key))] + [uid[i] for i in range(4)]

        (error, back_data, back_length) = self.card_write(self.mode_auth, buf)
        if not (self.dev_read(0x08) & 0x08) != 0:
            error = True

        if not error:
            self.authed = True

        return error

    def stop_crypto(self):
        """Ends operations with Crypto1 usage."""
        self.clear_bitmask(0x08, 0x08)
        self.authed = False

    def halt(self):
        """Switch state to HALT"""

        buf = [self.act_end, 0]

        self.clear_bitmask(0x08, 0x80)
        self.card_write(self.mode_transrec, buf)
        self.clear_bitmask(0x08, 0x08)
        self.authed = False

    def read(self, block_address):
        """
        Reads data from block. You should be authenticated before calling read.
        Returns tuple of (error state, read data).
        """
        buf = [self.act_read, block_address]
        crc = self.calculate_crc(buf)
        buf.append(crc[0])
        buf.append(crc[1])
        (error, back_data, back_length) = self.card_write(self.mode_transrec, buf)

        if len(back_data) != self.length:
            error = True

        return error, back_data

    def write(self, block_address, data):
        """
        Writes data to block. You should be authenticated before calling write.
        Returns error state.
        """
        buf = [self.act_write, block_address]
        crc = self.calculate_crc(buf)
        buf.append(crc[0])
        buf.append(crc[1])

        error, back_data, back_length = self.card_write(self.mode_transrec, buf)
        if back_length != 4 or (back_data[0] & 0x0F) != 0x0A:
            error = True

        if not error:
            buf_w = []
            for i in range(self.length):
                buf_w.append(data[i])

            crc = self.calculate_crc(buf_w)
            buf_w.append(crc[0])
            buf_w.append(crc[1])
            (error, back_data, back_length) = self.card_write(self.mode_transrec, buf_w)
            if back_length != 4 or (back_data[0] & 0x0F) != 0x0A:
                error = True

        return error

    def reset(self):
        self.dev_write(self.CommandReg, self.mode_reset)

    def cleanup(self):
        """
        Calls stop_crypto() if needed and cleanups GPIO.
        """
        if self.authed:
            self.stop_crypto()
        GPIO.cleanup()
        self.spi.close()
