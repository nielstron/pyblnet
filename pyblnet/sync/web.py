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

from ..protocol.flow import run_sync
from ..protocol.web import Response, TransportError, WebProtocol, probe


def _performer(base_url, timeout):
    """Perform the requests of the pyblnet.protocol.web flows on base_url with requests"""

    def perform(request):
        url = base_url + request.path
        try:
            if request.method == "POST":
                r = requests.post(
                    url, data=request.data, headers=request.headers, timeout=timeout
                )
            else:
                r = requests.get(url, headers=request.headers, timeout=timeout)
        except requests.exceptions.RequestException as err:
            raise TransportError(err) from err
        return Response(r.text, r.headers.get("Set-Cookie"))

    return perform


def _with_scheme(ip):
    if not ip.startswith("http://") and not ip.startswith("https://"):
        ip = "http://" + ip
    return ip


def blnet_test(ip, timeout=5, id=0):
    """
    Tests whether an BLNET answers under given ip
    Attributes:
        ip      IP of the BLNET
    """
    return run_sync(probe(), _performer(_with_scheme(ip), timeout))


class WebClient(object):
    """
    Interface for connecting with, collecting data from and controlling the BLNet
    via it's HTTP-interface
    Attributes:
        ip         the ip/domain of the BL-Net to connect to
        password   the password to log into the web interface provided
        timeout    timeout for http requests
    """

    _def_password = "0128"  # default password is 0128

    def __init__(self, ip, password=_def_password, timeout=5):
        """
        Constructor
        """
        assert isinstance(ip, str)
        assert password is None or isinstance(password, str)
        assert timeout is None or isinstance(timeout, int)
        ip = _with_scheme(ip)
        if not blnet_test(ip):
            raise ValueError("No BLNET found under given address: {}".format(ip))
        self.ip = ip
        self._timeout = timeout
        self.protocol = WebProtocol(password)

    @property
    def password(self):
        return self.protocol.password

    @property
    def current_taid(self):
        """TAID cookie in the form 'TAID="EEEE"'"""
        return self.protocol.current_taid

    def _run(self, flow):
        return run_sync(flow, _performer(self.ip, self._timeout))

    def __enter__(self):
        self.log_in()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log_out()

    def cookie_header(self):
        """
        Creates the header to pass the session TAID as cookie
        """
        return {"Cookie": self.current_taid}

    def logged_in(self):
        """
        Determines whether the object is still connected to the BLNET
        / Logged into the web interface
        """
        return self._run(self.protocol.logged_in())

    def log_in(self):
        """
        Logs into the BLNET interface, renews the TAID

        Return: Login successful
        """
        return self._run(self.protocol.log_in())

    def log_out(self):
        """
        Logs out of the BLNET interface

        Return: successful log out
        """
        return self._run(self.protocol.log_out())

    def set_node(self, node):
        """
        Selects the node at which the UVR of interest lies
        future requests will be sent at this particular UVR

        Return: Still logged in (indicating successful node change)
        """
        return self._run(self.protocol.set_node(node))

    def read_analog_values(self):
        """
        Reads all analog values (temperatures, speeds) from the web interface
        and returns list of quadruples of id, name, value, unit of measurement
        """
        return self._run(self.protocol.read_analog_values())

    def read_digital_values(self):
        """
        Reads all digital values (switches) from the web interface
        and returns list of quadruples of id, name, mode (AUTO/HAND), value
        (EIN/AUS)
        """
        return self._run(self.protocol.read_digital_values())

    def set_digital_value(self, digital_id, value):
        """
        Sets a digital value with given id to given value
        Accepts 'EIN' and everything evaluating to True
        as well as 'AUS' and everything evaluating to False
        and 'AUTO' as values
        Attributes:
            id       id of the device whichs state should be changed
            value    value to change the state to
        Return: still logged in (indicating successful set)
        """
        return self._run(self.protocol.set_digital_value(digital_id, value))

    def fetch(self, node=None):
        """
        Log in, select the node if given, read the analog and digital values
        and log out. Returns both lists, see read_analog_values and
        read_digital_values.
        """
        return self._run(self.protocol.fetch(node))

    def turn(self, digital_id, value, node=None):
        """
        Set a digital value in a session of its own, raises ConnectionError
        if it fails
        """
        return self._run(self.protocol.turn(digital_id, value, node))
