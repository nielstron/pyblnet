"""
The direct connection (TA port, PC-BLNET protocol) of the BL-NET without
I/O: the commands, how to read their replies, and the reads as flows (see
flow.py). pyblnet.sync.DirectClient runs them with a socket, pyblnet.aio.DirectClient with
asyncio streams.

This is basically a python port of a script by berwinter
https://github.com/berwinter/uvr1611/blob/master/lib/backend/blnet-connection.inc.php
It uses this protocol and is still very buggy
www.haus-terra.at/heizung/download/Schnittstelle/Schnittstelle_PC_Bootloader.pdf
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import struct

from .parser import Parser

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
# Seconds to wait when the BL-Net has no new data yet. Real devices answer
# GET_LATEST with "no data" for up to about 5 seconds after a read.
NO_DATA_WAIT = 2
MAX_RETRYS = 10
# Length of a WAIT_TIME reply: 0xBA, seconds to wait, checksum
WAIT_SIZE = 3
DATASET_SIZE = 61
LATEST_SIZE = 56

# Errors of malformed replies, raised as ConnectionError by the clients
INVALID_REPLY_ERRORS = (struct.error, IndexError, ValueError)


# The operations the flows yield
@dataclass(frozen=True)
class Connect:
    """Open the TCP connection to the BL-NET"""


@dataclass(frozen=True)
class Disconnect:
    """Close the TCP connection"""


@dataclass(frozen=True)
class Send:
    """Send all of data"""

    data: bytes


@dataclass(frozen=True)
class Receive:
    """Receive up to max_size bytes, b"" if the BL-NET closed the connection"""

    max_size: int


@dataclass(frozen=True)
class Sleep:
    """Wait for some seconds"""

    seconds: float


def checksum_ok(data):
    """Whether the last byte of data is the checksum of the others"""
    binary = struct.unpack("<{}B".format(len(data)), data)
    return sum(binary[:-1]) % 256 == binary[-1]


class DirectProtocol:
    """
    The state of a direct connection and the flows reading from it.
    The clients reset it (and close the connection) when a flow fails.
    """

    def __init__(self, reset=False):
        """
        :param reset: boolean, delete data on BL-Net after data receive
        """
        self.reset = reset
        self.connected = False
        self.mode = None
        self.count = None
        self.address = None

    def forget(self):
        """Forget the read state, after the connection was closed"""
        self.connected = False
        self.count = None
        self.address = None

    def _connect(self):
        if not self.connected:
            yield Connect()
            self.connected = True

    def _disconnect(self):
        yield Disconnect()
        self.connected = False

    def _query(self, command, length):
        """
        Send a command to the bootloader and wait for the response,
        if the response is at most 32 bytes long return immediately
        @throws ConnectionError BL-Net closed the connection
        """
        yield Send(command)
        data = b""
        # get response until length or less than 32 bytes
        while True:
            received = yield Receive(length)
            if not received:
                raise ConnectionError("BL-Net closed the connection")
            data += received
            if len(data) <= 32 or len(data) >= length:
                return data

    def _receive_exact(self, length):
        """
        Receive exactly length bytes
        @throws ConnectionError BL-Net closed the connection
        """
        data = b""
        while len(data) < length:
            received = yield Receive(length - len(data))
            if not received:
                raise ConnectionError("BL-Net closed the connection")
            data += received
        return data

    def _query_latest(self, command):
        """
        Send a GET_LATEST command and receive the complete reply.
        The BL-Net may send a reply in several TCP segments, so the length
        is derived from its first byte and the reply is read completely.
        Reading only part of it would leave the rest in the socket and
        shift every following reply by some bytes.
        @return a "no data", "wait" or data reply
        """
        yield Send(command)
        first = yield from self._receive_exact(1)
        if first[0] == GET_LATEST:
            # no new data available yet
            return first
        if first[0] == WAIT_TIME:
            return first + (yield from self._receive_exact(WAIT_SIZE - 1))
        return first + (yield from self._receive_exact(self._actual_size - 1))

    def check_mode(self):
        """
        Flow: check if the bootloader mode is supported
        @throws ConnectionError Mode not supported
        """
        yield from self._connect()
        self.mode = yield from self._query(GET_MODE, 1)
        yield from self._disconnect()

        if self.mode in [CAN_MODE, DL2_MODE, DL_MODE]:
            return True
        raise ConnectionError("BL-Net mode is not supported")

    def get_count(self):
        """
        Flow: the number of datasets in the bootloader memory
        """
        if not self.count:
            yield from self._connect()
            data = yield from self._query(GET_HEADER, 21)

            if checksum_ok(data):
                if self.mode == CAN_MODE:
                    frame_count = struct.unpack("<{}B".format(len(data)), data)[5]
                    (_, _, _, frame_count, _, start_address, end_address, _) = struct.unpack(
                        "<BB3sB{}s3s3sB".format(frame_count), data
                    )
                    self._address_inc = 64 * frame_count
                    self._can_frames = frame_count
                    self._actual_size = 57
                    self._fetch_size = 4 + 61 * frame_count
                elif self.mode == DL_MODE:
                    (_, _, start_address, end_address, _) = struct.unpack("<5sB3s3sB", data)
                    self._address_inc = 64
                    self._can_frames = 1
                    self._actual_size = 57
                    self._fetch_size = 65
                elif self.mode == DL2_MODE:
                    (_, _, start_address, end_address, _) = struct.unpack("<5s2s3s3sB", data)
                    self._address_inc = 128
                    self._can_frames = 1
                    self._actual_size = 113
                    self._fetch_size = 126

                self._address_end = (0x07FFFF // self._address_inc) * self._address_inc

                # check address validity
                if start_address != b"0xFFFFFF" and end_address != b"0xFFFFFF":
                    start_address = int.from_bytes(start_address, byteorder="little")
                    end_address = int.from_bytes(end_address, byteorder="little")
                    # fix addresses
                    if end_address > start_address:
                        self.count = ((end_address - start_address) / self._address_inc) + 1
                    else:
                        self.count = (
                            self._address_end + start_address - end_address
                        ) / self._address_inc
                    self.address = end_address
        if self.count:
            self.count = int(self.count)
            return self.count
        raise ConnectionError("Could not retreive count")

    def get_data(self, max_count=None):
        """Flow: read up to max_count datasets logged in the bootloader memory"""
        data = []
        count = yield from self.get_count()
        if isinstance(max_count, int):
            count = min(max_count, count)
        for _ in range(0, count):
            data.append((yield from self._fetch_data()))
        yield from self._end_read(True)
        return data

    def _fetch_data(self):
        """
        Fetch a dataset from the bootloader memory
        @throws: ConnectionError Data could not be retreived
        @return frame -> value mappings
        """
        if self.count and self.count > 0:
            yield from self._connect()

            # build address for bootloader
            addresses = [
                self.address & 0xFF,
                (self.address & 0x7F00) >> 7,
                (self.address & 0xFF8000) >> 15,
            ]
            command = struct.pack(
                "<6B",
                READ_DATA,
                addresses[0],
                addresses[1],
                addresses[2],
                1,
                (READ_DATA + 1 + sum(addresses)) % 256,
            )
            data = yield from self._query(command, self._fetch_size)

            if checksum_ok(data):
                # increment address
                self.address -= self._address_inc
                if self.address < 0:
                    self.address = self._address_end
                self.count -= 1
                return self._split_datasets(data)
            raise ConnectionError("Could not retreive data")

    def _split_datasets(self, data):
        """
        split binary string in datasets and parse dataset values
        @return frame -> value mappings
        """
        frames = {}
        if self.mode == CAN_MODE:
            for frame in range(0, self._can_frames):
                frames[frame] = Parser(
                    data[3 + DATASET_SIZE * frame : 3 + DATASET_SIZE * (frame + 1)]
                )
        elif self.mode == DL_MODE:
            frames[0] = Parser(data[:DATASET_SIZE])
        elif self.mode == DL2_MODE:
            frames[0] = Parser(data[:DATASET_SIZE])
            frames[1] = Parser(data[3 + DATASET_SIZE : 3 + DATASET_SIZE + DATASET_SIZE])

        start = 3 if self.mode == CAN_MODE else 0
        if data[start : start + DATASET_SIZE - 6] == b"0x00" * (DATASET_SIZE - 6):
            return False
        return {k: v.to_dict() for k, v in frames.items()}

    def _end_read(self, success=True):
        """
        End read, reset memory on bootloader
        """
        yield from self._connect()
        if (yield from self._query(END_READ, 1)) != END_READ:
            raise ConnectionError("End read command failed")
        # reset data if configured
        if success and self.reset:
            if (yield from self._query(RESET_DATA, 1)) != RESET_DATA:
                raise ConnectionError("Reset memory failed")
        self.count = None
        self.address = None
        yield from self._disconnect()

    def get_latest(self, max_retries=MAX_RETRYS):
        """
        Flow: the latest (current) data
        @throws ConnectionError could not get data from BLNet
        @return frame -> value mappings
        """
        yield from self._connect()
        yield from self.get_count()
        frames = {}
        info = {"sleep": {}, "got": {}, "timeout": []}

        for frame in range(0, self._can_frames):
            command = struct.pack("<2B", GET_LATEST, frame + 1)
            sleeps = []
            for n in range(0, max_retries):
                data = yield from self._query_latest(command)

                if data == bytes([GET_LATEST]):
                    # no new data available yet ("Synchronisation" in TA's spec)
                    yield Sleep(NO_DATA_WAIT)
                elif checksum_ok(data):
                    if data[0] == WAIT_TIME:
                        sleeps.append(data[1])
                        yield from self._disconnect()
                        yield Sleep(data[1])
                        yield from self._connect()
                    else:
                        info["got"][frame] = n
                        frames.update(self._split_latest(data, frame))
                        break
                else:
                    # Unexpected bytes may still be on their way, reconnect
                    # so that they can't end up in the next reply
                    yield from self._disconnect()
                    yield from self._connect()
            else:
                # BL-Net did not send data for this frame within max_retries
                info["timeout"].append(frame)
            info["sleep"][frame] = sleeps
        yield from self._end_read(True)
        if len(frames) > 0:
            frames["date"] = datetime.now()
            frames["info"] = info
            return frames
        raise ConnectionError("Could not get latest data")

    def _split_latest(self, data, frame):
        """
        Split the reply to GET_LATEST
        @return frame -> value mappings
        """
        frames = {}
        if self.mode == CAN_MODE:
            frames[frame] = Parser(data[1 : LATEST_SIZE + 1])
        elif self.mode == DL_MODE:
            frames[0] = Parser(data[1 : LATEST_SIZE + 1])
        elif self.mode == DL2_MODE:
            frames[0] = Parser(data[1 : LATEST_SIZE + 1])
            frames[1] = Parser(data[LATEST_SIZE + 1 : 2 * LATEST_SIZE + 1])
        return {k: v.to_dict() for k, v in frames.items()}
