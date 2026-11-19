"""Read and control the BL-NET via the web interface and/or the direct connection"""
from __future__ import annotations

from urllib.parse import urlparse

from ..protocol.values import add_direct, add_web, empty_data, find_value
from . import direct, web


class Client:
    """
    Read and control the BL-NET via the web interface and/or the direct
    connection, see pyblnet.sync.Client. session is the aiohttp session for the
    web interface.
    """

    def __init__(self, web_client=None, direct_client=None, max_retries=5):
        """Use create()"""
        self.web = web_client
        self.direct = direct_client
        self.max_retries = max_retries

    @classmethod
    async def create(
        cls,
        address,
        session=None,
        web_port=80,
        password=None,
        ta_port=40000,
        timeout=5,
        max_retries=5,
        use_web=True,
        use_ta=False,
    ):
        assert isinstance(address, str)
        web_client = direct_client = None
        if use_web:
            if session is None:
                raise ValueError("The web interface needs an aiohttp session")
            web_client = await web.Client.create(
                "{}:{}".format(address, web_port), session, password, timeout
            )
        if use_ta:
            host = urlparse(address).hostname or address
            direct_client = await direct.Client.create(host, ta_port, timeout=timeout)
        return cls(web_client, direct_client, max_retries)

    async def close(self):
        """Close the direct connection, if open"""
        if self.direct:
            await self.direct.close()

    async def fetch(self, node=None):
        """
        Fetch all available data about selected node
        (defaults to active node on the device)
        """
        data = empty_data()
        if self.web:
            add_web(data, *await self.web.fetch(node))
        if self.direct:
            latest = await self.direct.get_latest(self.max_retries)
            add_direct(data, latest[0], self.web is not None)
        return data

    async def turn_on(self, digital_id, can_node=None):
        return await self._turn(digital_id, "EIN", can_node)

    async def turn_off(self, digital_id, can_node=None):
        return await self._turn(digital_id, "AUS", can_node)

    async def turn_auto(self, digital_id, can_node=None):
        return await self._turn(digital_id, "AUTO", can_node)

    async def _turn(self, digital_id, value, can_node=None):
        if not self.web:
            raise EnvironmentError("Can't set values with blnet web disabled")
        return await self.web.turn(digital_id, value, can_node)

    async def get_value(self, name=None, id=None, type="digital", ret="value", cached=None):
        """See pyblnet.sync.Client.get_value"""
        if name is None and id is None:
            return None
        if cached is None:
            cached = await self.fetch()
        return (*find_value(cached, name, id, type, ret), cached)
