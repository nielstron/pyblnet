"""Read and control the BL-NET via the web interface and/or the direct connection"""
from __future__ import annotations

from ..protocol.client import ClientBase, direct_host, web_address
from ..protocol.flow import AsyncRunner
from . import direct, web


class Client(AsyncRunner, ClientBase):
    """
    Read and control the BL-NET via the web interface and/or the direct
    connection, see pyblnet.protocol.client.ClientBase for its methods, which
    are awaitable here. Use create() to connect.
    """

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
        """
        See pyblnet.sync.Client, session is the aiohttp session for the web
        interface
        """
        assert isinstance(address, str)
        web_client = direct_client = None
        if use_web:
            if session is None:
                raise ValueError("The web interface needs an aiohttp session")
            web_client = await web.Client.create(
                web_address(address, web_port), session, password, timeout
            )
        if use_ta:
            direct_client = await direct.Client.create(direct_host(address), ta_port, timeout=timeout)
        return cls(web_client, direct_client, max_retries)

    async def close(self):
        """Close the direct connection, if open"""
        if self.direct:
            await self.direct.close()
