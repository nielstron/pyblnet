'''
Created on 09.08.2018

This class relies heavily on the following script by berwinter
https://github.com/berwinter/uvr1611/blob/master/lib/backend/blnet-connection.inc.php

@author: Niels
'''
import struct

# Parser constant
# 1 bit
DIGITAL_ON = 1;
DIGITAL_OFF = 0;
# 8 bit
SPEED_ACTIVE = 0x80;
SPEED_MASK = 0x1F;
# 16 bit
INT16_POSITIVE_MASK = 0xFFFF;
SIGN_BIT = 0x8000;
POSITIVE_VALUE_MASK = 0x0FFF;
TYPE_MASK = 0x7000;
TYPE_NONE = 0x0000;
TYPE_DIGITAL = 0x1000;
TYPE_TEMP = 0x2000;
TYPE_VOLUME = 0x3000;
TYPE_RADIATION = 0x4000;
TYPE_RAS = 0x7000;
RAS_POSITIVE_MASK = 0x01FF;
# 32 bit
INT32_MASK = 0xFFFFFFFF;
INT32_SIGN = 0x80000000

class BLNETParser:
    
    def __init__(self, data):
        '''
        parse a binary string containing a dataset
        Provides access to the values of a dataset as object properties
        @param data: byte string
        '''
        # check if dataset contains time information
        # (fetched from bootloader storage)
        if len(data) == 61:
            (_, seconds, minutes, hours, days, months, years) = struct.unpack(
              '!55sBBBBBB', data)
            self.date = "20{:02d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                years, months, days, hours, minutes, seconds)
            
        (_, digital, speed, active, power1, kWh1,
         MWh1, power2, kWh2, MWh2) = struct.unpack(
             '!32sH4sBLHHLHH', data)
        
        analog = struct.unpack('!{}{}'.format('H'*16, 'x'*(len(data)-32)))

        self.analog = {}
        for channel in range(0, 16):
            self.analog[channel] = self._convert_analog(analog[channel])
        
        self.digital = {}
        for channel in range(0, 16):
            self.digital[channel] = self._convert_digital(digital[channel])

        self.speed = {}
        for channel in range(0, 4):
            self.speed[channel] = self._convert_speed(speed[channel])
        

    def to_dict(self):
        '''
        Turn parsed data into parser object
        @return dict
        '''
        return self.__dict__