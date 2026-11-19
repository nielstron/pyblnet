#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 13.08.2018

General high-level BLNET interface, blocking. The API is in
pyblnet.protocol.client.ClientBase.

@author: Nielstron
"""
from ..protocol.client import ClientBase
from ..protocol.flow import _FACTORY, SyncRunner
from . import direct, web


class Client(SyncRunner, ClientBase):
    """
    Read and control the BL-NET via the web interface and/or the direct
    connection, see pyblnet.protocol.client.ClientBase for its arguments and
    methods. Make it with create().
    """

    _direct_client_class = direct.Client

    def _new_web_client(self, ip, password, timeout):
        return web.Client(ip, password, timeout, _factory=_FACTORY)
