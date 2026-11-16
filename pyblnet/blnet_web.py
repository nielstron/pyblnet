#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 26.09.2017

A module for connecting with, collecting data from and controlling the BLNet 
via it's HTTP-interface

@author: Nielstron
"""

import requests
import html
import re
from builtins import int
from html.parser import HTMLParser

# An input on the inputs page: a measured value with unit, or the state of a
# digital input. The value of a digital input is "1" (on) or "0" (off), like
# the direct connection reports it.
INPUT_PATTERN = re.compile(
    r"(?P<id>\d+):&nbsp;(?P<name>.+)\n(&nbsp;){3,6}"
    r"(?:(?P<value>(-&nbsp;)?\d+,\d+) (?P<unit_of_measurement>.+?) &nbsp;&nbsp;"
    r"|(?P<state>AUS|EIN|OFF|ON)(&nbsp;)+)PAR?"
)
DIGITAL_INPUT_STATES = {"AUS": "0", "OFF": "0", "EIN": "1", "ON": "1"}


class _ElementTextParser(HTMLParser):
    """
    Collects the text of all elements with the given tag and class or id.
    Entities like &nbsp; are kept as written and <br> becomes a newline,
    which is what the regular expressions below expect.
    """

    def __init__(self, tag, cls=None, id=None):
        super().__init__(convert_charrefs=False)
        self.tag = tag
        self.cls = cls
        self.id = id
        # text of each matching element, in document order
        self.texts = []
        # for each open element with self.tag: its index in self.texts,
        # or None if it doesn't match. Matching elements can be nested.
        self._open = []

    def _matches(self, attrs):
        attrs = dict(attrs)
        return (self.cls is None or self.cls in (attrs.get("class") or "").split()) and (
            self.id is None or attrs.get("id") == self.id
        )

    def handle_starttag(self, tag, attrs):
        if tag == self.tag:
            if self._matches(attrs):
                self.texts.append("")
                self._open.append(len(self.texts) - 1)
            else:
                self._open.append(None)
        elif tag == "br":
            self.handle_data("\n")

    def handle_endtag(self, tag):
        if tag == self.tag and self._open:
            self._open.pop()

    def handle_data(self, data):
        for index in self._open:
            if index is not None:
                self.texts[index] += data

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")


def _element_texts(page, tag, cls=None, id=None):
    """Texts of all elements in page with the given tag and class or id"""
    parser = _ElementTextParser(tag, cls, id)
    parser.feed(page)
    parser.close()
    return parser.texts


def _element_text(page, tag, cls=None, id=None):
    """Text of the first such element, empty if there is none"""
    texts = _element_texts(page, tag, cls, id)
    return texts[0] if texts else ""


def blnet_test(ip, timeout=5, id=0):
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
    # either a 'Zugriff verweigert' message is shown
    if "BL-Net".lower() in _element_text(r.text, "title").lower():
        return True
    # or (more often) the BL-NET Menü
    if "BL-NET" in _element_text(r.text, "div", id="head"):
        return True
    return False


class BLNETWeb(object):
    """
    Interface for connecting with, collecting data from and controlling the BLNet
    via it's HTTP-interface
    Attributes:
        ip         the ip/domain of the BL-Net to connect to
        password   the password to log into the web interface provided
        timeout    timeout for http requests
    """

    ip = ""
    _def_password = "0128"  # default password is 0128
    password = ""
    current_taid = ""  # TAID cookie in the form 'TAID="EEEE"'

    def __init__(self, ip, password=_def_password, timeout=5):
        """
        Constructor
        """
        assert isinstance(ip, str)
        assert password is None or isinstance(password, str)
        assert timeout is None or isinstance(timeout, int)
        if not ip.startswith("http://") and not ip.startswith("https://"):
            ip = "http://" + ip
        if not blnet_test(ip):
            raise ValueError("No BLNET found under given address: {}".format(ip))
        self.ip = ip
        self.password = password
        self._timeout = timeout

    def __enter__(self):
        self.log_in()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log_out()

    def logged_in(self):
        """
        Determines whether the object is still connected to the BLNET
        / Logged into the web interface
        """
        if self.password is None:
            return True
        # check if a request to a restricted page returns a cookie if
        # we have sent one (if our cookie is the current one this
        # would be the case)
        try:
            r = requests.get(
                # restricted page is chosen to be small in data
                # so that it can be quickly loaded
                self.ip + "/par.htm?blp=A1200101&1238653",
                headers=self.cookie_header(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return False
        return r.headers.get("Set-Cookie") is not None

    def cookie_header(self):
        """
        Creates the header to pass the session TAID as cookie
        """
        headers = {"Cookie": self.current_taid}
        return headers

    def log_in(self):
        """
        Logs into the BLNET interface, renews the TAID

        Return: Login successful
        """
        if self.logged_in():
            return True
        payload = {"blu": 1, "blp": self.password, "bll": "Login"}  # log in as experte
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            r = requests.post(
                self.ip + "/main.html",
                data=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return False
        self.current_taid = r.headers.get("Set-Cookie")
        # try two times to log in
        i = 0
        while i < 2:
            i += 1
            if self.logged_in():
                return True
        return False

    def log_out(self):
        """
        Logs out of the BLNET interface

        Return: successful log out
        """
        if self.password is None:
            return True
        try:
            requests.get(
                self.ip + "/main.html?blL=1",
                headers=self.cookie_header(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return False
        return not self.logged_in()

    def set_node(self, node):
        """
        Selects the node at which the UVR of interest lies
        future requests will be sent at this particular UVR

        Return: Still logged in (indicating successful node change)
        """
        # send the request to change the node
        try:
            r = requests.get(
                self.ip + "/can.htm?blaB=" + str(node),
                headers=self.cookie_header(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return False
        # return whether we we're still logged in => setting went well
        return self.password is None or r.headers.get("Set-Cookie") is not None

    def read_analog_values(self):
        """
        Reads all analog values (temperatures, speeds) from the web interface
        and returns list of quadruples of id, name, value, unit of measurement
        """
        try:
            r = requests.get(
                self.ip + "/580500.htm",
                headers=self.cookie_header(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return None
        # get the element containing the interesting information
        texts = _element_texts(r.text, "div", cls="c")
        # in case of access denied or other errors, return None
        if len(texts) < 2:
            return None
        data_raw = texts[1]

        # collect data in an array
        data = list()

        # search for data by regular expression
        for match in INPUT_PATTERN.finditer(data_raw):
            # convert html entities to unicode characters,
            # replace &nbsp; by " " since it is not unescaped as expected
            entry = {
                "id": match["id"],
                "name": html.unescape(match["name"].replace("&nbsp;", " ")),
            }
            if match["state"] is not None:
                entry["value"] = DIGITAL_INPUT_STATES[match["state"]]
                entry["unit_of_measurement"] = None
                entry["type"] = "digital"
            else:
                # replace decimal "," by "." and remove "&nbsp;" completely
                entry["value"] = match["value"].replace("&nbsp;", "").replace(",", ".")
                entry["unit_of_measurement"] = html.unescape(
                    match["unit_of_measurement"].replace("&nbsp;", " ")
                )
            data.append(entry)
        return data

    def read_digital_values(self):
        """
        Reads all digital values (switches) from the web interface
        and returns list of quadruples of id, name, mode (AUTO/HAND), value
        (EIN/AUS)
        """
        try:
            r = requests.get(
                self.ip + "/580600.htm",
                headers=self.cookie_header(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return None
        # Check if we didn't fail in access
        if "BL-Net Zugang verweigert" in _element_text(r.text, "title"):
            return None
        # get the element containing the interesting information
        texts = _element_texts(r.text, "div", cls="c")
        if len(texts) < 2:
            return None
        data_raw = texts[1]

        # collect data in an array
        data = list()

        # search for data by regular expression
        match_iter = re.finditer(
            r"(?P<id>\d+):&nbsp;(?P<name>.+)\n&nbsp;&nbsp;&nbsp;&nbsp;(?P<mode>(AUTO|HAND))/(?P<value>(AUS|EIN))",
            data_raw,
        )
        # parse a dict of the match and save them all in a list
        for match in match_iter:
            match_dict = match.groupdict()
            # convert html entities to unicode characters
            for key, value in match_dict.items():
                value = value.replace("&nbsp;", " ")
                match_dict[key] = html.unescape(value)
            # and append formatted dict
            data.append(match_dict)
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
        Return: still logged in (indicating successful set)
        """

        digital_id = int(digital_id)
        # throw error for wrong id's
        if digital_id < 1:
            raise ValueError(
                "Device id can't be smaller than 1, was {}".format(digital_id)
            )
        if digital_id > 15:
            raise ValueError(
                "Device id can't be larger than 15, was {}".format(digital_id)
            )
        # transform input value to 'EIN' or 'AUS'
        if isinstance(value, str):
            if value.lower() == "AUTO".lower() or value == "3":
                value = "3"  # 3 means auto
            elif (
                value.lower() == "EIN".lower()
                or value == "2"
                or value.lower() == "on".lower()
            ):
                value = "2"  # 2 means turn on
            elif (
                value.lower() == "AUS".lower()
                or value == "1"
                or value.lower() == "off".lower()
            ):
                value = "1"  # 1 means turn off
            else:
                raise ValueError("Illegal input string {}".format(value))
        elif isinstance(value, int) and not isinstance(value, bool):
            if value in (1, 2, 3):
                value = str(value)
            elif value == 0:
                value = "1"
            else:
                raise ValueError("Illegal input integer {}".format(value))
        else:
            # value can be interpreted as a true value
            if value:
                value = "2"  # 2 means turn on
            else:
                value = "1"  # 1 means turn off
        assert value in ["1", "2", "3"]

        # convert id to hexvalue so that 10 etc become A...
        hex_repr = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, "A", "B", "C", "D", "E", "F"]
        if digital_id > 9:
            digital_id = hex_repr[digital_id]

        # submit data to website
        try:
            r = requests.get(
                "{}/580600.htm?blw91A1200{}={}".format(self.ip, digital_id, value),
                headers=self.cookie_header(),
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException:
            return False

        # return whether we we're still logged in => setting went well
        return self.password is None or r.headers.get("Set-Cookie") is not None
