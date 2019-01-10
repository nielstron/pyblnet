#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 13.08.2018

General high-level BLNET interface.

Abstracts from actual type of connection to the BLNET and provides as much functionality
as possible.

@author: Niels
"""
from pyblnet.blnet_web import BLNETWeb
from pyblnet.blnet_conn import BLNETDirect

from urllib.parse import urlparse


class BLNET(object):
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

    def __init__(self,
                 address,
                 web_port=80,
                 password=None,
                 ta_port=40000,
                 timeout=5,
                 max_retries=5,
                 use_web=True,
                 use_ta=True):
        """
        If a connection (Web or TA/Direct) should not be used,
        set the corresponding use_* to False
        Params:
        @param ta_port: Port for direct TCP Connection
        """
        assert (isinstance(address, str))
        assert (web_port is None or isinstance(web_port, int))
        assert (ta_port is None or isinstance(ta_port, int))
        assert (timeout is None or isinstance(timeout, int))
        self.address = address
        self.timeout = timeout
        self.max_retries = max_retries
        self.blnet_web = None
        self.blnet_direct = None
        if use_web:
            self.blnet_web = BLNETWeb("{}:{}".format(address, web_port),
                                      password, timeout)
        if use_ta:
            # The address might not have a resulting hostname
            # especially not if not prefixed with http://
            # see https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse
            host = urlparse(address).hostname or address
            self.blnet_direct = BLNETDirect(host, ta_port)

    def fetch(self, node=None):
        """
        Fetch all available data about selected node
        (defaults to active node on the device)
        """
        data = {
            'analog': {},
            'digital': {},
            'speed': {},
            'energy': {},
            'power': {},
        }
        if self.blnet_web:
            if node is not None:
                self.blnet_web.set_node(node)
            data['analog'] = self._convert_web(
                self.blnet_web.read_analog_values())
            data['digital'] = self._convert_web(
                self.blnet_web.read_digital_values())
        if self.blnet_direct:
            direct = self.blnet_direct.get_latest(self.max_retries)[0]
            # Override values for analog and digital as values are
            # expected to be more precise here
            for domain in ['analog', 'digital']:
                for id, value in direct[domain].items():
                    if data[domain].get(id) is not None:
                        data[domain][id]['value'] = value
            for domain in ['speed', 'energy', 'power']:
                for id, value in direct[domain].items():
                    if value is None:
                        continue
                    data[domain][id] = {'value': value}
        return data

    def turn_on(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node on
        Return: no error during set operation
        """
        return self._turn(digital_id, 'EIN', can_node)

    def turn_off(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node off
        Return: no error during set operation
        """
        return self._turn(digital_id, 'AUS', can_node)

    def turn_auto(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node to "AUTO"/ give control over to UVR
        Return: no error during set operation
        """
        return self._turn(digital_id, 'AUTO', can_node)

    def _turn(self, digital_id, value, can_node=None):
        if self.blnet_web:
            if not self.blnet_web.log_in():
                raise ConnectionError('Could not log in')
            if can_node is not None:
                if not self.blnet_web.set_node(can_node):
                    raise ConnectionError('Could not set node')
            if not self.blnet_web.set_digital_value(digital_id, value):
                raise ConnectionError('Failed to set value')
            else:
                return True
        else:
            raise EnvironmentError('Can\'t set values with blnet web disabled')

    def get_value(self,
                  name=None,
                  id=None,
                  type='digital',
                  ret='value',
                  cached=None):
        """
          higher level interface to get a value or mode by name or id
          ret: can be 'value', 'mode'
          returns the value  if ret='value' or the mode if ret='mode' as first return value
                  and the dictionary containing name, value, id and mode as a second return value
          cached: in order to prevent polling data from BLNet with every call, 
                  the data can be fetched once and stored and passed to this function


        """
        val = None
        dic = None
        if name is None and id is None: return val
        if cached is None:
            cached = self.fetch()
        for key, v in cached[type].items():
            if str(v['name']) == str(name) or str(v['id']) == str(id):
                val = v[ret]
                dic = v

        return val, dic, cached

    def get_digital_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type='digital', ret='value', name=name, id=id, cached=cached)

    def get_digital_mode(self, name=None, id=None, cached=None):
        return self.get_value(
            type='digital', ret='mode', name=name, id=id, cached=cached)

    def get_analog_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type='analog', ret='value', name=name, id=id, cached=cached)

    def get_energy_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type='energy', ret='value', name=name, id=id, cached=cached)

    def get_speed_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type='speed', ret='value', name=name, id=id, cached=cached)

    def get_power_value(self, name=None, id=None, cached=None):
        return self.get_value(
            type='power', ret='value', name=name, id=id, cached=cached)

    @staticmethod
    def _convert_web(values):
        """
        Converts data returned by blnet_web to nice data
        """
        data = {}
        try:
            for sensor in values:
                data[int(sensor['id'])] = sensor
        except TypeError:
            pass
        return data
