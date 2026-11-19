#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 09.08.2018

The direct connection to the BL-NET over a socket. The protocol is in
pyblnet.protocol.direct, this module runs it.

@author: Niels
"""
from socket import socket, getaddrinfo, SOCK_STREAM, IPPROTO_TCP
from time import sleep

from ..protocol.direct import (
    INVALID_REPLY_ERRORS,
    MAX_RETRYS,
    Connect,
    Protocol,
    Disconnect,
    Receive,
    Send,
    Sleep,
)
from ..protocol.flow import run_sync


class Client(object):
    """
    A class for establishing a direct connection to the BLNET (rather than
    scraping the web interface)

    It uses this protocol and is still very buggy
    www.haus-terra.at/heizung/download/Schnittstelle/Schnittstelle_PC_Bootloader.pdf
    """

    def __init__(self, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        """
        Constructor
        :param address: string, Address of the BL-Net device
        :param port: integer, Port of the bl-net device for connection
        :param reset: boolean, delete data on BL-Net after data receive
        :param timeout: float, timeout in seconds for the connection
        """
        assert isinstance(address, str)
        assert isinstance(port, int)
        assert isinstance(reset, bool)
        self.address = address
        self.port = port
        self.reset = reset
        # 0 would make the socket non-blocking, treat it like None (no timeout)
        self._timeout = timeout or None
        self._socket = None
        self.protocol = Protocol(reset)
        self._check_mode()

    def _run(self, flow):
        """
        Run a flow of the protocol. If it fails, close the connection and
        forget the read state, so that the next call starts afresh.
        Malformed replies are raised as ConnectionError.
        """
        try:
            return run_sync(flow, self._perform)
        except INVALID_REPLY_ERRORS as ex:
            self._reset()
            raise ConnectionError(f"Invalid reply from BL-Net: {ex}") from ex
        except BaseException:
            self._reset()
            raise

    def _perform(self, operation):
        if isinstance(operation, Send):
            self._socket.sendall(operation.data)
        elif isinstance(operation, Receive):
            return self._socket.recv(operation.max_size)
        elif isinstance(operation, Sleep):
            sleep(operation.seconds)
        elif isinstance(operation, Connect):
            self._connect()
        elif isinstance(operation, Disconnect):
            self._disconnect()
        else:
            raise TypeError(f"Unknown operation {operation}")

    def _connect(self):
        """
        Connect to bootloader via TCP
        @throws ConnectionError Connection failed
        """
        if self._socket is None:
            available = getaddrinfo(self.address, self.port, 0, SOCK_STREAM, IPPROTO_TCP)
            for (family, socktype, proto, _, sockaddr) in available:
                try:
                    self._socket = socket(family, socktype, proto)
                    self._socket.settimeout(self._timeout)
                    self._socket.connect(sockaddr)
                    break
                except OSError:
                    self._socket.close()
                    self._socket = None
            if self._socket is None:
                raise ConnectionError("Could not connect to BLNET")

    def _disconnect(self):
        """
        Disconnect from bootloader via TCP
        """
        self._socket.close()
        self._socket = None

    def _reset(self):
        """
        Close the connection if open and forget the read state
        """
        if self._socket is not None:
            self._disconnect()
        self.protocol.forget()

    @property
    def _mode(self):
        return self.protocol.mode

    def _check_mode(self):
        """
        Check if Bootloader Mode is supported
        @throws ConnectionError Mode not supported
        """
        return self._run(self.protocol.check_mode())

    def get_count(self):
        """
        Get the number of datasets in the bootloader memory
        @return number of datasets in bootloader memory
        """
        return self._run(self.protocol.get_count())

    def _get_data(self, max_count=None):
        return self._run(self.protocol.get_data(max_count))

    def get_latest(self, max_retries=MAX_RETRYS):
        """
        Fetch latest (current) data from the BLNet
        @throws checksum error
        @throws ConnectionError could not get data from BLNet
        @return Array of frame -> value mappings
        """
        return self._run(self.protocol.get_latest(max_retries))
