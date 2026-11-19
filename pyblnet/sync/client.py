#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 13.08.2018

General high-level BLNET interface.

Abstracts from actual type of connection to the BLNET and provides as much functionality
as possible.

@author: Niels
"""
from ..protocol.values import add_direct, add_web, convert_web, empty_data, find_value
from .direct import DirectClient
from .web import WebClient

from urllib.parse import urlparse


class Client(object):
    """
    General high-level BLNET interface.

    Abstracts from actual type of connection to the BLNET and provides as much functionality
    as possible.
    Attributes:
    address      ip address of the BLNET
    web_port     port of the HTTP interface
    password     password for authenticating on the HTTP interface
    ta_port      port of the PC-BLNET interface
    timeout      timeout for requests
    max_retries  maximum number of connection retries before aborting
    use_web      boolean about whether to make use of the HTTP interface
    use_ta       boolean about whether to make use of the (buggy) PC-BLNET interface
    """

    def __init__(
        self,
        address,
        web_port=80,
        password=None,
        ta_port=40000,
        timeout=5,
        max_retries=5,
        use_web=True,
        use_ta=False,
    ):
        """
        If a connection (Web or TA/Direct) should not be used,
        set the corresponding use_* to False
        Params:
        @param ta_port: Port for direct TCP Connection
        """
        assert isinstance(address, str)
        assert web_port is None or isinstance(web_port, int)
        assert ta_port is None or isinstance(ta_port, int)
        assert timeout is None or isinstance(timeout, int)
        self.address = address
        self.timeout = timeout
        self.max_retries = max_retries
        self.web = None
        self.direct = None
        if use_web:
            self.web = WebClient(
                "{}:{}".format(address, web_port), password, timeout
            )
        if use_ta:
            # The address might not have a resulting hostname
            # especially not if not prefixed with http://
            # see https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse
            host = urlparse(address).hostname or address
            self.direct = DirectClient(host, ta_port, timeout=timeout)

    def fetch(self, node=None):
        """
        Fetch all available data about selected node
        (defaults to active node on the device)
        """
        data = empty_data()
        if self.web:
            add_web(data, *self.web.fetch(node))
        if self.direct:
            add_direct(
                data, self.direct.get_latest(self.max_retries)[0], self.web is not None
            )
        return data

    def turn_on(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node on
        Return: no error during set operation
        """
        return self._turn(digital_id, "EIN", can_node)

    def turn_off(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node off
        Return: no error during set operation
        """
        return self._turn(digital_id, "AUS", can_node)

    def turn_auto(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node to "AUTO"/ give control over to UVR
        Return: no error during set operation
        """
        return self._turn(digital_id, "AUTO", can_node)

    def _turn(self, digital_id, value, can_node=None):
        if self.web:
            return self.web.turn(digital_id, value, can_node)
        else:
            raise EnvironmentError("Can't set values with blnet web disabled")

    def get_value(self, name=None, id=None, type="digital", ret="value", cached=None):
        """
        higher level interface to get a value or mode by name or id
        ret: can be 'value', 'mode'
        returns the value  if ret='value' or the mode if ret='mode' as first return value
                and the dictionary containing name, value, id and mode as a second return value
        cached: in order to prevent polling data from BLNet with every call,
                the data can be fetched once and stored and passed to this function


        """
        if name is None and id is None:
            return None
        if cached is None:
            cached = self.fetch()
        return (*find_value(cached, name, id, type, ret), cached)

    def get_digital_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type="digital", ret="value", name=name, id=id, cached=cached
        )

    def get_digital_mode(self, name=None, id=None, cached=None):
        return self.get_value(
            type="digital", ret="mode", name=name, id=id, cached=cached
        )

    def get_analog_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type="analog", ret="value", name=name, id=id, cached=cached
        )

    def get_energy_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type="energy", ret="value", name=name, id=id, cached=cached
        )

    def get_speed_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type="speed", ret="value", name=name, id=id, cached=cached
        )

    def get_power_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type="power", ret="value", name=name, id=id, cached=cached
        )

    _convert_web = staticmethod(convert_web)
