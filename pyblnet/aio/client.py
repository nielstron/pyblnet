"""Read and control the BL-NET via the web interface and/or the direct connection"""
from __future__ import annotations

from ..protocol.client import ClientBase
from ..protocol.flow import _FACTORY, AsyncRunner
from . import direct, web


class Client(AsyncRunner, ClientBase):
    """
    Read and control the BL-NET via the web interface and/or the direct
    connection, see pyblnet.protocol.client.ClientBase for its arguments and
    methods, which are awaitable here. session is the aiohttp session for the
    web interface. Make it with await create(address, session, ...), close
    it with close().
    """

    _direct_client_class = direct.Client

    def __init__(self, address, session=None, *args, **kwargs):
        self.session = session
        super().__init__(address, *args, **kwargs)

    def _new_web_client(self, ip, password, timeout):
        if self.session is None:
            raise ValueError("The web interface needs an aiohttp session")
        return web.Client(ip, self.session, password, timeout, _factory=_FACTORY)

    async def close(self):
        """Close the direct connection, if open"""
        if self.direct:
            await self.direct.close()
