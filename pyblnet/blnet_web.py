#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 26.09.2017

@author: Nielstron
"""

import requests
from htmldom import htmldom
import html
import re
from builtins import int


def test_blnet(ip, timeout=5):
    """
    Tests whether an BLNET answers under given ip
    Attributes:
        ip      IP of the BLNET
    """
    if not ip.startswith("http://") and not ip.startswith("https://"):
        ip = "http://" + ip
    try:
        r = requests.get(ip, timeout=timeout)
    except requests.exceptions.RequestException:
        return False
    # Parse  DOM object from HTMLCode
    dom = htmldom.HtmlDom().createDom(r.text)
    # either a 'Zugriff verweigert' message is shown
    if 'BL-Net Zugang verweigert' in dom.find('title').text():
        return True
    # or (more often) the BL-NET Menü
    if 'BL-NET' in dom.find('div#head').text():
        return True
    return False


class BLNETWeb(object):
    """
    Interface to communicate with the UVR1611 over his web surface (BL-Net)
    Attributes:
        ip         The ip/domain of the UVR1611/BL-Net to connect to
        password   the password to log into the web interface provided
    """
    ip = ""
    _def_password = "0128"  # default password is 0128
    password = ""
    current_taid = ""  # TAID cookie in the form 'TAID="EEEE"'

    def __init__(self, ip, password=_def_password, timeout=5):
        """
        Constructor
        """
        assert (isinstance(ip, str))
        assert (password is None or isinstance(password, str))
        assert (timeout is None or isinstance(timeout, int))
        if not ip.startswith("http://") and not ip.startswith("https://"):
            ip = "http://" + ip
        if not test_blnet(ip):
            raise ValueError(
                'No BLNET found under given address: {}'.format(ip))
        self.ip = ip
        if password is None:
            password = self._def_password
        self.password = password
        self._timeout = timeout

    def logged_in(self):
        """
        Determines whether the object is still connected to the BLNET
        / Logged into the web interface
        """
        # check if a request to a restricted page returns a cookie if
        # we have sent one (if our cookie is the current one this
        # would be the case)
        try:
            r = requests.get(
                # restricted page is chosen to be small in data
                # so that it can be quickly loaded
                self.ip + "/par.htm?blp=A1200101&1238653",
                headers=self.cookie_header(),
                timeout=self._timeout)
        except requests.exceptions.RequestException:
            return False
        return r.headers.get('Set-Cookie') is not None

    def cookie_header(self):
        """
        Creates the header to pass the session TAID as cookie
        """
        headers = {'Cookie': self.current_taid}
        return headers

    def log_in(self):
        """
        Logs into the BLNET interface, renews the TAID
        
        Return: Login successful
        """
        if self.logged_in(): return True
        payload = {
            'blu': 1,  # log in as experte
            'blp': self.password,
            'bll': "Login"
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            r = requests.post(
                self.ip + '/main.html',
                data=payload,
                headers=headers,
                timeout=self._timeout)
        except requests.exceptions.RequestException:
            return False
        # try two times to log in
        i = 0
        while i < 2:
            self.current_taid = r.headers.get('Set-Cookie')
            i += 1
            if self.logged_in():
                return True
        return False

    def log_out(self):
        """
        Logs out of the BLNET interface
        
        Return: successful log out
        """
        try:
            requests.get(
                self.ip + "/main.html?blL=1",
                headers=self.cookie_header(),
                timeout=self._timeout)
        except requests.exceptions.RequestException:
            return False
        return not self.logged_in()

    def set_node(self, node):
        """
        Selects the node at which the UVR of interest lies
        future requests will be sent at this particular UVR
        
        Return: Successful node change
        """
        # ensure to be logged in
        if not self.log_in():
            return False

        # send the request to change the node
        try:
            r = requests.get(
                self.ip + "/can.htm?blaA=" + str(node),
                headers=self.cookie_header(),
                timeout=self._timeout)
        except requests.exceptions.RequestException:
            return False
        # return whether we we're still logged in => setting went well
        return r.headers.get('Set-Cookie') is not None

    def read_analog_values(self):
        """
        Reads all analog values (temperatures, speeds) from the web interface
        and returns list of quadruples of id, name, value, unit of measurement
        """
        # ensure to be logged in
        if not self.log_in(): return None

        if not self.logged_in(): self.log_in()
        try:
            r = requests.get(
                self.ip + "/580500.htm",
                headers=self.cookie_header(),
                timeout=self._timeout)
        except requests.exceptions.RequestException:
            return None
        # Parse  DOM object from HTMLCode
        dom = htmldom.HtmlDom().createDom(r.text)
        # get the element containing the interesting information
        dom = dom.find("div.c")[1]
        # filter out the text
        data_raw = dom.text()

        # collect data in an array
        data = list()

        # search for data by regular expression
        match_iter = re.finditer(
            "(?P<id>\d+):&nbsp;(?P<name>.+)\n" +
            "(&nbsp;){3,6}(?P<value>\d+,\d+) " +
            "(?P<unit_of_measurement>.+?) &nbsp;&nbsp;PAR?", data_raw)
        match = next(match_iter, False)
        # parse a dict of the match and save them all in a list
        while match:
            match_dict = match.groupdict()
            # convert html entities to unicode characters
            for key in match_dict.keys():
                match_dict[key] = html.unescape(match_dict[key])
                # also replace decimal "," by "."
                match_dict[key] = match_dict[key].replace(",", ".")
            # and append formatted dict
            data.append(match_dict)
            match = next(match_iter, False)
        return data

    def read_digital_values(self):
        """
        Reads all digital values (switches) from the web interface
        and returns list of quadruples of id, name, mode (AUTO/HAND), value 
        (EIN/AUS)
        """
        # ensure to be logged in
        if not self.log_in(): return None

        if not self.logged_in(): self.log_in()
        try:
            r = requests.get(
                self.ip + "/580600.htm",
                headers=self.cookie_header(),
                timeout=self._timeout)
        except requests.exceptions.RequestException:
            return None
        # Parse  DOM object from HTMLCode
        dom = htmldom.HtmlDom().createDom(r.text)
        # get the element containing the interesting information
        dom = dom.find("div.c")[1]

        # filter out the text
        data_raw = dom.text()

        # collect data in an array
        data = list()

        # search for data by regular expression
        match_iter = re.finditer(
            "(?P<id>\d+):&nbsp;(?P<name>.+)\n" +
            "&nbsp;&nbsp;&nbsp;&nbsp;(?P<mode>(AUTO|HAND))/" +
            "(?P<value>(AUS|EIN))", data_raw)
        match = next(match_iter, False)
        # parse a dict of the match and save them all in a list
        while match:
            match_dict = match.groupdict()
            # convert html entities to unicode characters
            for key in match_dict.keys():
                match_dict[key] = html.unescape(match_dict[key])
            # and append formatted dict
            data.append(match_dict)
            match = next(match_iter, False)
        return data

    def set_digital_value(self, digital_id, value):
        """
        Sets a digital value with given id to given value 
        Accepts 'EIN' and everything evaluating to True
        as well as 'AUS' and everything evaluating to False
        and 'AUTO' as values
        Attributes:
            id       id of the device whichs state should be changed
            value    value to change the state to
        Return: successful set
        """

        digital_id = int(digital_id)
        # throw error for wrong id's
        if digital_id < 1:
            raise ValueError('Device id can\'t be smaller than 1')
        # ensure to be logged in
        if not self.log_in():
            return False

        # transform input value to 'EIN' or 'AUS'
        if value == 'AUTO':
            value = '3'  # 3 means auto
        elif value != 'AUS' and value:
            value = '2'  # 2 means turn on
        else:
            value = '1'  # 1 means turn off

        # convert id to hexvalue so that 10 etc become A...
        hex_repr = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'D', 'E', 'F']
        if digital_id > 9:
            digital_id = hex_repr[digital_id]

        # submit data to website
        try:
            r = requests.get(
                "{}/580600.htm?blw91A1200{}={}".format(self.ip, digital_id,
                                                       value),
                headers=self.cookie_header(),
                timeout=self._timeout)
        except requests.exceptions.RequestException:
            return False

        # return whether we we're still logged in => setting went well
        return r.headers.get('Set-Cookie') is not None
