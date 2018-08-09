'''
Created on 09.08.2018

This class relies heavily on the following script by berwinter
https://github.com/berwinter/uvr1611/blob/master/lib/backend/blnet-connection.inc.php

@author: Niels
'''
from builtins import str, int
from socket import socket, getaddrinfo, SOCK_STREAM, IPPROTO_TCP
import struct

# Constants for the UVR Communication
CAN_MODE = b"\xDC";
DL_MODE = b"\xA8";
DL2_MODE = b"\xD1";
GET_MODE = b"\x81";
GET_HEADER = b"\xAA";
GET_LATEST = b"0xAB";
READ_DATA = b"0xAC";
END_READ = b"\xAD";
RESET_DATA = b"\xAF";
WAIT_TIME = b"0xBA";
MAX_RETRYS = 10;
DATASET_SIZE = 61;
LATEST_SIZE = 56;

class BLNETDirect(object):
    '''
    A class for establishing a direct connection to the BLNET (rather than
    scraping the web interface)
    '''

    def __init__(self, address, port=40000, reset=False):
        '''
        Constructor
        @param address: string, Address of the BL-Net device
        @param port: integer, Port of the bl-net device for connection
        @param reset: boolean, delete data on BL-Net after data receive
        '''
        assert(isinstance(address, str))
        assert(isinstance(port, int))
        assert(isinstance(reset, bool))
        self.address = address
        self.port = port
        self.reset = reset
        self._mode = None
        self._socket = None
        self._count = None
        self._check_mode()
    
    def _check_mode(self):
        '''
        Check if Bootloader Mode is supported
        @throws ConnectionError Mode not supported
         '''
        self.connect()
        self._mode = self.query(GET_MODE, 1)
        self.disconnect()
        
        if self._mode in [CAN_MODE, DL2_MODE, DL_MODE]:
            return True
        raise ConnectionError('BL-Net mode is not supported')
    
    def connect(self):
        '''
        Connect to bootloader via TCP
        @throws ConnectionError Connection failed
        '''
        if self._socket is None:
            available = getaddrinfo(
                self.address,
                self.port,
                0,
                SOCK_STREAM,
                IPPROTO_TCP
            )
            for (family, socktype, proto, _, sockaddr) in available:
                try:
                    self._socket = socket(family, socktype, proto)
                    self._socket.connect(sockaddr)
                    break
                except:
                    self._socket = None
            if self._socket is None:
                raise ConnectionError('Could not connect to BLNET')
    
    def disconnect(self):
        '''
        Disconnect from bootloader via TCP
        '''
        self._socket.close()
        self._socket = None
    
    def query(self, command, length):
        '''
        Send a command to the bootloader and wait for the response
        if response is less then 32 bytes long return immediately
        @param commmand: string only ascii (needs byte length == string length)
        @param length: int length of response
        @throws ConnectionError error when querying
        @return Binary: string
        '''
        if len(command) == self._socket.send(command):
            data = b""
            # get response until length or less than 32 bytes
            while True:
                data += self._socket.recv(length)
                if len(data) <= 32 or len(data) >= length:
                    break
            return data

        self.disconnect()
        raise ConnectionError('Error while querying command {}'.format(command))
    
    def start_read(self):
        '''
        Start to read on the bootloader
        @return number of frames available
        '''
        return self.get_count()
    
    def get_count(self):
        '''
        Get the number of datasets in the bootloader memory
        @return number of datasets in bootloader memory
        '''
        if self._count is None:
            self.connect()
            data = self.query(GET_HEADER, 21)
            
            if self.checksum(data):
                if self._mode == CAN_MODE:
                    frame_count = struct.unpack('!{}B'.format(len(data)),
                                                data)[5]
                    (type, version, timestamp, frame_count, _, start_address,
                     end_address, checksum) = struct.unpack(
                         '!BB3sB{}s3s3sB'.format(frame_count), data)
                    self._address_inc = 64 * frame_count
                    self._can_frames = frame_count
                    self._actual_size = 57
                    self._fetch_size = 4 + 61 * frame_count
                
                self._address_end = ((0x07FFFF // self._address_inc)
                                       * self._address_inc)
                # check address validity
                if (start_address[0] != b"0xFF" or
                    start_address[1] != b"0xFF" or
                    start_address[2] != b"0xFF" or
                    end_address[0] != b"0xFF" or
                    end_address[1] != b"0xFF" or
                    end_address[2] != b"0xFF"):
                    # fix addresses
                    if end_address > start_address:
                        # calculate count
                        self._count = ((end_address - start_address)
                                       / self._address_inc) + 1
                    else:
                        self._count = ((self._address_end + start_address
                                        - end_address) / self._address_inc)
            
        return self._can_frames        

    def checksum(self, data):
        '''
        Verify the checksum
        @param string $data Binary string to check
        @return boolean
        '''
        binary = struct.unpack('!{}B'.format(len(data)), data)
        checksum = binary[-1]
        
        sum = 0
        # build sum
        for byte in binary[:-1]:
            sum += byte
        # verify
        return sum % 256 == checksum
    
        
        
        
