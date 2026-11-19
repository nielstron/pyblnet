"""Read and control the BL-NET via the web interface and/or the direct connection"""
from __future__ import annotations

from urllib.parse import urlparse

from ..protocol.values import add_direct, add_web, empty_data, find_value
from .direct import BLNETDirect
from .web import BLNETWeb


class BLNET:
    """
    Read and control the BL-NET via the web interface and/or the direct
    connection, see pyblnet.BLNET. session is the aiohttp session for the
    web interface.
    """

    def __init__(self, blnet_web=None, blnet_direct=None, max_retries=5):
        """Use create()"""
        self.blnet_web = blnet_web
        self.blnet_direct = blnet_direct
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
        blnet_web = blnet_direct = None
        if use_web:
            if session is None:
                raise ValueError("The web interface needs an aiohttp session")
            blnet_web = await BLNETWeb.create(
                "{}:{}".format(address, web_port), session, password, timeout
            )
        if use_ta:
            host = urlparse(address).hostname or address
            blnet_direct = await BLNETDirect.create(host, ta_port, timeout=timeout)
        return cls(blnet_web, blnet_direct, max_retries)

    async def close(self):
        """Close the direct connection, if open"""
        if self.blnet_direct:
            await self.blnet_direct.close()

    async def fetch(self, node=None):
        """
        Fetch all available data about selected node
        (defaults to active node on the device)
        """
        data = empty_data()
        if self.blnet_web:
            add_web(data, *await self.blnet_web.fetch(node))
        if self.blnet_direct:
            latest = await self.blnet_direct.get_latest(self.max_retries)
            add_direct(data, latest[0], self.blnet_web is not None)
        return data

    async def turn_on(self, digital_id, can_node=None):
        return await self._turn(digital_id, "EIN", can_node)

    async def turn_off(self, digital_id, can_node=None):
        return await self._turn(digital_id, "AUS", can_node)

    async def turn_auto(self, digital_id, can_node=None):
        return await self._turn(digital_id, "AUTO", can_node)

    async def _turn(self, digital_id, value, can_node=None):
        if not self.blnet_web:
            raise EnvironmentError("Can't set values with blnet web disabled")
        return await self.blnet_web.turn(digital_id, value, can_node)

    async def get_value(self, name=None, id=None, type="digital", ret="value", cached=None):
        """See pyblnet.BLNET.get_value"""
        if name is None and id is None:
            return None
        if cached is None:
            cached = await self.fetch()
        return (*find_value(cached, name, id, type, ret), cached)
