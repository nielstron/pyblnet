"""
Read and control the BL-NET via the web interface and/or the direct
connection, without the I/O: the flows combining both, and the API of
pyblnet.sync.Client and pyblnet.aio.Client.
"""
from urllib.parse import urlparse

from .values import add_direct, add_web, empty_data, find_value
from .web import Request


def web_address(address, web_port):
    """Address of the web interface"""
    return "{}:{}".format(address, web_port)


def direct_host(address):
    """Host of the direct connection"""
    # The address might not have a resulting hostname
    # especially not if not prefixed with http://
    # see https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse
    return urlparse(address).hostname or address


class Protocol:
    """
    The flows using the web and/or direct protocol, either may be None.
    They yield the operations of both, see ClientBase._perform.
    """

    def __init__(self, web, direct, max_retries):
        self.web = web
        self.direct = direct
        self.max_retries = max_retries

    def fetch(self, node=None):
        """Flow: all available data about the node (default: the active one)"""
        data = empty_data()
        if self.web:
            add_web(data, *(yield from self.web.fetch(node)))
        if self.direct:
            latest = yield from self.direct.guarded(self.direct.get_latest(self.max_retries))
            add_direct(data, latest[0], self.web is not None)
        return data

    def turn(self, digital_id, value, node=None):
        """Flow: set a digital output via the web interface"""
        if not self.web:
            raise EnvironmentError("Can't set values with blnet web disabled")
        return (yield from self.web.turn(digital_id, value, node))

    def get_value(self, name=None, id=None, type="digital", ret="value", cached=None):
        """Flow: see ClientBase.get_value"""
        if name is None and id is None:
            return None
        if cached is None:
            cached = yield from self.fetch()
        return (*find_value(cached, name, id, type, ret), cached)


class ClientBase:
    """
    General high-level BLNET interface, without the I/O.

    Abstracts from actual type of connection to the BLNET and provides as much functionality
    as possible. The methods run flows with self._run, see pyblnet.protocol.flow.
    Attributes:
    web          the client of the web interface, None if not used
    direct       the client of the direct connection, None if not used
    max_retries  maximum number of connection retries before aborting
    """

    def __init__(self, web=None, direct=None, max_retries=5):
        self.web = web
        self.direct = direct
        self.max_retries = max_retries

    @property
    def protocol(self):
        return Protocol(
            self.web.protocol if self.web else None,
            self.direct.protocol if self.direct else None,
            self.max_retries,
        )

    def _perform(self, operation):
        """HTTP requests go to the web client, the rest to the direct one"""
        client = self.web if isinstance(operation, Request) else self.direct
        return client._perform(operation)

    def fetch(self, node=None):
        """
        Fetch all available data about selected node
        (defaults to active node on the device)
        """
        return self._run(self.protocol.fetch(node))

    def turn_on(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node on
        Return: no error during set operation
        """
        return self._run(self.protocol.turn(digital_id, "EIN", can_node))

    def turn_off(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node off
        Return: no error during set operation
        """
        return self._run(self.protocol.turn(digital_id, "AUS", can_node))

    def turn_auto(self, digital_id, can_node=None):
        """
        Turn switch with given id on given node to "AUTO"/ give control over to UVR
        Return: no error during set operation
        """
        return self._run(self.protocol.turn(digital_id, "AUTO", can_node))

    def get_value(self, name=None, id=None, type="digital", ret="value", cached=None):
        """
        higher level interface to get a value or mode by name or id
        ret: can be 'value', 'mode'
        returns the value  if ret='value' or the mode if ret='mode' as first return value
                and the dictionary containing name, value, id and mode as a second return value
        cached: in order to prevent polling data from BLNet with every call,
                the data can be fetched once and stored and passed to this function
        """
        return self._run(self.protocol.get_value(name, id, type, ret, cached))

    def get_digital_value(self, name=None, id=None, cached=None):
        return self.get_value(type="digital", ret="value", name=name, id=id, cached=cached)

    def get_digital_mode(self, name=None, id=None, cached=None):
        return self.get_value(type="digital", ret="mode", name=name, id=id, cached=cached)

    def get_analog_value(self, name=None, id=None, cached=None):
        return self.get_value(type="analog", ret="value", name=name, id=id, cached=cached)

    def get_energy_value(self, name=None, id=None, cached=None):
        return self.get_value(type="energy", ret="value", name=name, id=id, cached=cached)

    def get_speed_value(self, name=None, id=None, cached=None):
        return self.get_value(type="speed", ret="value", name=name, id=id, cached=cached)

    def get_power_value(self, name=None, id=None, cached=None):
        return self.get_value(type="power", ret="value", name=name, id=id, cached=cached)
