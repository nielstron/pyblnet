#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 26.09.2017

A module for connecting with, collecting data from and controlling the BLNet
via it's HTTP-interface. The protocol is in pyblnet.protocol.web, this module
runs it with requests.

@author: Nielstron
"""

import requests

from ..protocol.flow import SyncRunner, run_sync
from ..protocol.web import DEFAULT_PASSWORD, ClientBase, Response, TransportError, base_url, probe


def _performer(url, timeout):
    """Perform the requests of the pyblnet.protocol.web flows on url with requests"""

    def perform(request):
        try:
            if request.method == "POST":
                r = requests.post(
                    url + request.path, data=request.data, headers=request.headers, timeout=timeout
                )
            else:
                r = requests.get(url + request.path, headers=request.headers, timeout=timeout)
        except requests.exceptions.RequestException as err:
            raise TransportError(err) from err
        return Response(r.text, r.headers.get("Set-Cookie"))

    return perform


def blnet_test(ip, timeout=5):
    """
    Tests whether an BLNET answers under given ip
    Attributes:
        ip      IP of the BLNET
    """
    return run_sync(probe(), _performer(base_url(ip), timeout))


class Client(SyncRunner, ClientBase):
    """
    The web interface of the BL-NET, see pyblnet.protocol.web.ClientBase for
    its methods. Make it with create(). Use it in a with statement to log in
    and out.
    """

    def __init__(self, ip, password=DEFAULT_PASSWORD, timeout=5, *, _factory=None):
        super().__init__(ip, password, timeout, _factory=_factory)
        self._perform = _performer(self.ip, timeout)

    def __enter__(self):
        self.log_in()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log_out()
