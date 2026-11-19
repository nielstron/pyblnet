"""The web interface of the BL-NET, with aiohttp"""
from __future__ import annotations

import asyncio

import aiohttp
from yarl import URL

from ..protocol.flow import AsyncRunner, run_async
from ..protocol.web import DEFAULT_PASSWORD, ClientBase, Response, TransportError, base_url, probe


def _performer(session, url, timeout):
    """Perform the requests of the pyblnet.protocol.web flows on url with aiohttp"""
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    async def perform(request):
        try:
            async with session.request(
                request.method,
                # the BL-NET expects its URLs exactly as written, e.g. "?blp=A1200101&1238653"
                URL(url + request.path, encoded=True),
                data=request.data,
                headers=request.headers,
                timeout=client_timeout,
            ) as r:
                # decode like requests does, the BL-NET doesn't send a charset
                text = await r.text(encoding=r.charset or "latin-1")
                return Response(text, r.headers.get("Set-Cookie"))
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise TransportError(err) from err

    return perform


async def blnet_test(session, ip, timeout=5):
    """Whether a BL-NET answers under the given address"""
    return await run_async(probe(), _performer(session, base_url(ip), timeout))


class Client(AsyncRunner, ClientBase):
    """
    The web interface of the BL-NET, see pyblnet.protocol.web.ClientBase for
    its methods, which are awaitable here. Make it with await create(ip,
    session, ...). Use it in an async with statement to log in and out.
    """

    def __init__(self, ip, session, password=DEFAULT_PASSWORD, timeout=5, *, _factory=None):
        super().__init__(ip, password, timeout, _factory=_factory)
        self._perform = _performer(session, self.ip, timeout)

    async def __aenter__(self):
        await self.log_in()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.log_out()
