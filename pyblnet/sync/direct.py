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

from ..protocol.direct import ClientBase, Connect, Disconnect, Receive, Send, Sleep
from ..protocol.flow import SyncRunner


class Client(SyncRunner, ClientBase):
    """
    The direct connection (TA port) of the BL-NET over a socket, see
    pyblnet.protocol.direct.ClientBase for its methods. Raises
    ConnectionError if the BL-NET mode is not supported.
    """

    def __init__(self, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        super().__init__(address, port, reset, timeout)
        self._socket = None
        self.check_mode()

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
            self._socket.close()
            self._socket = None
        else:
            raise TypeError(f"Unknown operation {operation}")

    def _connect(self):
        """
        Connect to bootloader via TCP
        @throws ConnectionError Connection failed
        """
        available = getaddrinfo(self.address, self.port, 0, SOCK_STREAM, IPPROTO_TCP)
        for (family, socktype, proto, _, sockaddr) in available:
            try:
                self._socket = socket(family, socktype, proto)
                self._socket.settimeout(self._timeout)
                self._socket.connect(sockaddr)
                return
            except OSError:
                self._socket.close()
                self._socket = None
        raise ConnectionError("Could not connect to BLNET")
