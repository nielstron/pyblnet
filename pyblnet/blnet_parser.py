#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 09.08.2018

This is basically a python port of of a script by berwinter
https://github.com/berwinter/uvr1611/blob/master/lib/backend/blnet-connection.inc.php

author: Niels
"""
import struct
from datetime import datetime

# Parser constant
# 1 bit
DIGITAL_ON = 1
DIGITAL_OFF = 0
# 8 bit
SPEED_ACTIVE = 0x80
SPEED_MASK = 0x1F
# 16 bit
INT16_POSITIVE_MASK = 0xFFFF
SIGN_BIT = 0x8000
POSITIVE_VALUE_MASK = 0x0FFF
TYPE_MASK = 0x7000
TYPE_NONE = 0x0000
TYPE_DIGITAL = 0x1000
TYPE_TEMP = 0x2000
TYPE_VOLUME = 0x3000
TYPE_RADIATION = 0x4000
TYPE_RAS = 0x7000
RAS_POSITIVE_MASK = 0x01FF
# 32 bit
INT32_MASK = 0xFFFFFFFF
INT32_SIGN = 0x80000000


class BLNETParser:
    def __init__(self, data):
        """
        parse a binary string containing a dataset
        Provides access to the values of a dataset as object properties
        @param data: byte string
        """
        # check if dataset contains time information
        # (fetched from bootloader storage)
        if len(data) == 61:
            (_, seconds, minutes, hours, days, months, years) = struct.unpack(
                '<55sBBBBBB', data)
            self.date = datetime(2000 + years, months, days, hours, minutes,
                                 seconds)

        # Only parse preceding data
        data = data[:55]
        power = [0, 0]
        kWh = [0, 0]
        MWh = [0, 0]
        (_, digital, speed, active, power[0], kWh[0], MWh[0], power[1], kWh[1],
         MWh[1]) = struct.unpack('<32sH4sBLHHLHH', data)

        analog = struct.unpack(
            '<{}{}'.format('H' * 16, 'x' * (len(data) - 32)), data)

        self.analog = {}
        for channel in range(0, 16):
            self.analog[channel + 1] = round(
                self._convert_analog(analog[channel]), 3)

        self.digital = {}
        for channel in range(0, 16):
            self.digital[channel + 1] = self._convert_digital(digital, channel)

        self.speed = {}
        for channel in range(0, 4):
            self.speed[channel + 1] = round(
                self._convert_speed(speed[channel]), 3)

        self.energy = {}
        for channel in range(0, 2):
            self.energy[channel + 1] = round(
                self._convert_energy(MWh[channel], kWh[channel], active,
                                     channel), 3)

        self.power = {}
        for channel in range(0, 2):
            self.power[channel + 1] = round(
                self._convert_power(power[channel], active, channel), 3)

    def to_dict(self):
        """
        Turn parsed data into parser object
        @return dict
        """
        return self.__dict__

    def _convert_analog(self, value):
        """
        Convert int to correct float
        @param value: short unsigned int that was returned by blnet
        @return float with correct sensor value
        """

        mask = value & TYPE_MASK
        if mask == TYPE_TEMP:
            return self._calculate_value(value, 0.1)
        elif mask == TYPE_VOLUME:
            return self._calculate_value(value, 4)
        elif mask == TYPE_DIGITAL:
            if value & SIGN_BIT:
                return 1
            else:
                return 0
        elif mask == TYPE_RAS:
            return self._calculate_value(value, 0.1, RAS_POSITIVE_MASK)
        elif mask in [TYPE_RADIATION, TYPE_NONE] or True:
            return self._calculate_value(value)

    def _convert_digital(self, value, position):
        """
        Check if bit at given position is set (=1)
        """
        if value & (0x1 << (position)):
            return DIGITAL_ON
        else:
            return DIGITAL_OFF

    def _convert_speed(self, value):
        """
        Check if speed is activated and return its value
        """
        if value & SPEED_ACTIVE:
            return None
        else:
            return value & SPEED_MASK

    def _convert_energy(self, mwh, kwh, active, position):
        """
        Check if heat meter is activated on a given position
        @return its energy
        """
        if active & position:
            kwh = self._calculate_value(kwh, 0.1, INT16_POSITIVE_MASK)
            return mwh * 1000 + kwh
        else:
            return None

    def _convert_power(self, value, active, position):
        """
        checks if heat meter is activated at given position
        @return its power
        """
        if active & position:
            return self._calculate_value(value, 1 / 2560, INT32_MASK,
                                         INT32_SIGN)
        else:
            return None

    def _calculate_value(self,
                         value,
                         multiplier=1,
                         positive_mask=POSITIVE_VALUE_MASK,
                         signbit=SIGN_BIT):
        result = value & positive_mask
        if value & signbit:
            result = -((result ^ positive_mask) + 1)
        return result * multiplier
