#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 09.08.2018

This is basically a python port of of a script by berwinter
https://github.com/berwinter/uvr1611/blob/master/lib/backend/blnet-connection.inc.php

@author: Niels
"""
from builtins import str, int
from socket import socket, getaddrinfo, SOCK_STREAM, IPPROTO_TCP
import struct
from .blnet_parser import BLNETParser
from time import sleep
from datetime import datetime
import math

# Constants for the UVR Communication
CAN_MODE = b"\xDC"
DL_MODE = b"\xA8"
DL2_MODE = b"\xD1"
GET_MODE = b"\x81"
GET_HEADER = b"\xAA"
GET_LATEST = 0xAB
READ_DATA = 0xAC
END_READ = b"\xAD"
RESET_DATA = b"\xAF"
WAIT_TIME = 0xBA
MAX_RETRYS = 10
DATASET_SIZE = 61
LATEST_SIZE = 56


class BLNETDirect(object):
    """
    A class for establishing a direct connection to the BLNET (rather than
    scraping the web interface)
    
    It uses this protocol and is still very buggy
    www.haus-terra.at/heizung/download/Schnittstelle/Schnittstelle_PC_Bootloader.pdf
    """

    def __init__(self, address, port=40000, reset=False):
        """
        Constructor
        @param address: string, Address of the BL-Net device
        @param port: integer, Port of the bl-net device for connection
        @param reset: boolean, delete data on BL-Net after data receive
        """
        assert (isinstance(address, str))
        assert (isinstance(port, int))
        assert (isinstance(reset, bool))
        self.address = address
        self.port = port
        self.reset = reset
        self._mode = None
        self._socket = None
        self._count = None
        self._check_mode()

    def get_count(self):
        """
        Get the number of datasets in the bootloader memory
        @return number of datasets in bootloader memory
        """
        if not self._count:
            self._connect()
            data = self._query(GET_HEADER, 21)

            if self._checksum(data):
                if self._mode == CAN_MODE:
                    frame_count = struct.unpack('<{}B'.format(len(data)),
                                                data)[5]
                    (type, version, timestamp, frame_count, _, start_address,
                     end_address, checksum) = struct.unpack(
                         '<BB3sB{}s3s3sB'.format(frame_count), data)
                    self._address_inc = 64 * frame_count
                    self._can_frames = frame_count
                    self._actual_size = 57
                    self._fetch_size = 4 + 61 * frame_count
                elif self._mode == DL_MODE:
                    (_, device, start_address, end_address,
                     checksum) = struct.unpack('<5sB3s3sB')
                    self._address_inc = 64
                    self._can_frames = 1
                    self._actual_size = 57
                    self._fetch_size = 65
                elif self._mode == DL2_MODE:
                    (_, device, start_address, end_address,
                     checksum) = struct.unpack('<5s2s3s3sB')
                    self._address_inc = 128
                    self._can_frames = 1
                    self._actual_size = 113
                    self._fetch_size = 126

                self._address_end = (
                        (0x07FFFF // self._address_inc) * self._address_inc
                )

                # check address validity
                if (start_address != b'0xFFFFFF'
                        and end_address != b'0xFFFFFF'):
                    start_address = int.from_bytes(
                        start_address, byteorder='little')
                    end_address = int.from_bytes(
                        end_address, byteorder='little')
                    # fix addresses
                    if end_address > start_address:
                        # calculate count
                        self._count = ((end_address - start_address) /
                                       self._address_inc) + 1
                    else:
                        self._count = (
                            (self._address_end + start_address - end_address) /
                            self._address_inc)
                    self._address = end_address
        if self._count:
            self._count = int(self._count)
            return self._count
        else:
            raise ConnectionError('Could not retreive count')

    def _get_data(self, max_count=None):
        data = []
        try:
            count = self._start_read()
            if isinstance(max_count, int):
                count = min(max_count, count)
            for _ in range(0, count):
                data.append(self._fetch_data())
            self._end_read(True)
            return data
        finally:
            self._end_read(False)
            return data

    def _check_mode(self):
        """
        Check if Bootloader Mode is supported
        @throws ConnectionError Mode not supported
         """
        self._connect()
        self._mode = self._query(GET_MODE, 1)
        self._disconnect()

        if self._mode in [CAN_MODE, DL2_MODE, DL_MODE]:
            return True
        raise ConnectionError('BL-Net mode is not supported')

    def _connect(self):
        """
        Connect to bootloader via TCP
        @throws ConnectionError Connection failed
        """
        if self._socket is None:
            available = getaddrinfo(self.address, self.port, 0, SOCK_STREAM,
                                    IPPROTO_TCP)
            for (family, socktype, proto, _, sockaddr) in available:
                try:
                    self._socket = socket(family, socktype, proto)
                    self._socket.connect(sockaddr)
                    break
                except:
                    self._socket = None
            if self._socket is None:
                raise ConnectionError('Could not connect to BLNET')

    def _disconnect(self):
        """
        Disconnect from bootloader via TCP
        """
        self._socket.close()
        self._socket = None

    def _query(self, command, length):
        """
        Send a command to the bootloader and wait for the response
        if response is less then 32 bytes long return immediately
        @param commmand: string only ascii (needs byte length == string length)
        @param length: int length of response
        @throws ConnectionError error when querying
        @return Binary: byte string
        """
        if len(command) == self._socket.send(command):
            data = b""
            # get response until length or less than 32 bytes
            while True:
                data += self._socket.recv(length)
                if len(data) <= 32 or len(data) >= length:
                    break
            return data

        self._disconnect()
        raise ConnectionError(
            'Error while querying command {}'.format(command))

    def _start_read(self):
        """
        Start to read on the bootloader
        @return number of frames available
        """
        return self.get_count()

    def _checksum(self, data):
        """
        Verify the checksum
        @param byte string $data Binary string to check
        @return boolean
        """
        binary = struct.unpack('<{}B'.format(len(data)), data)
        checksum = binary[-1]

        sum = 0
        # build sum
        for byte in binary[:-1]:
            sum += byte
        # verify
        return sum % 256 == checksum

    def _fetch_data(self):
        """
        Fetch datasets from bootloader memory
        @throws: ConnectionError Data could not be retreived
        @return Array of frame -> value mappings
        """
        if self._count and self._count > 0:
            self._connect()

            # build address for bootloader
            addresses = [
                self._address & 0xFF, (self._address & 0x7F00) >> 7,
                (self._address & 0xFF8000) >> 15
            ]

            # build command
            command = struct.pack('<6B', READ_DATA, addresses[0], addresses[1],
                                  addresses[2], 1,
                                  (READ_DATA + 1 + sum(addresses)) % 256)

            data = self._query(command, self._fetch_size)

            if self._checksum(data):
                # increment address
                self._address -= self._address_inc
                if self._address < 0:
                    self._address = self._address_end
                self._count -= 1
                return self._split_datasets(data)
            raise ConnectionError('Could not retreive data')

    def _split_datasets(self, data):
        """
        split binary string in datasets and parse dataset values
        @param data: byte string
        @return Array of frame -> value mappings
        """
        frames = {}
        if self._mode == CAN_MODE:
            for frame in range(0, self._can_frames):
                frames[frame] = BLNETParser(data[3 + DATASET_SIZE * frame:3 +
                                                 DATASET_SIZE * (frame + 1)])
        elif self._mode == DL_MODE:
            frames[0] = BLNETParser(data[:DATASET_SIZE])
        elif self._mode == DL2_MODE:
            frames[0] = BLNETParser(data[:DATASET_SIZE])
            frames[1] = BLNETParser(
                data[3 + DATASET_SIZE:3 + DATASET_SIZE + DATASET_SIZE])

        start = 0

        if self._mode == CAN_MODE:
            start = 3
        if data[start:start + DATASET_SIZE -
                6] == b'0x00' * (DATASET_SIZE - 6):
            return False
        else:
            return {k: v.to_dict() for k, v in frames.items()}

    def _end_read(self, success=True):
        """
        End read, reset memory on bootloader
        """
        self._connect()
        # Send end read command
        if self._query(END_READ, 1) != END_READ:
            raise ConnectionError('End read command failed')
        # reset data if configured
        if success and self.reset:
            if self._query(RESET_DATA, 1) != RESET_DATA:
                raise ConnectionError('Reset memory failed')
        self._count = None
        self._address = None
        self._disconnect()

    def get_latest(self, max_retries=MAX_RETRYS):
        """
        Fetch latest (current) data from the BLNet
        @throws checksum error
        @throws ConnectionError could not get data from BLNet
        @return Array of frame -> value mappings
        """
        self._connect()
        self.get_count()
        frames = {}
        info = {'sleep': {}, 'got': {}}

        # for all frames
        for frame in range(0, self._can_frames):
            # build command
            command = struct.pack("<2B", GET_LATEST, frame + 1)
            # try 4 times
            sleeps = []
            for n in range(0, max_retries):
                data = self._query(command, self._actual_size)

                if self._checksum(data):
                    binary = struct.unpack("<{}".format("B" * len(data)), data)

                    if binary[0] == WAIT_TIME:
                        sleeps.append(binary[1])
                        self._disconnect()
                        # wait some seconds
                        sleep(binary[1])
                        self._connect()
                    else:
                        info['got'][frame] = n
                        frames.update(self._split_latest(data, frame))
                        break
            # TODO this looks suspicious
            if n == max_retries - 1:
                frames[frame] = 'timeout'
            info['sleep'][frame] = sleeps
        self._end_read(True)
        if len(frames) > 0:
            frames['date'] = datetime.now()
            frames['info'] = info
            return frames
        raise ConnectionError("Could not get latest data")

    def _split_latest(self, data, frame):
        """
        Split binary string by fetch latest 
        @param data: bytestring
        @param frame: int
        @return Array of frame -> value mappings
        """
        frames = {}
        if self._mode == CAN_MODE:
            frames[frame] = BLNETParser(data[1:LATEST_SIZE + 1])
        elif self._mode == DL_MODE:
            frames[0] = BLNETParser(data[1:LATEST_SIZE + 1])
        elif self._mode == DL2_MODE:
            frames[0] = BLNETParser(data[1:LATEST_SIZE + 1])
            frames[1] = BLNETParser(data[LATEST_SIZE + 1:2 * LATEST_SIZE + 1])

        return {k: v.to_dict() for k, v in frames.items()}
