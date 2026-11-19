"""The web interface of the BL-NET, with aiohttp"""
from __future__ import annotations

import asyncio

import aiohttp
from yarl import URL

from ..protocol.flow import run_async
from ..protocol.web import Response, TransportError, WebProtocol, probe


def _with_scheme(ip):
    if not ip.startswith("http://") and not ip.startswith("https://"):
        ip = "http://" + ip
    return ip


def _performer(session, base_url, timeout):
    """Perform the requests of the pyblnet.protocol.web flows on base_url with aiohttp"""
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    async def perform(request):
        # the BL-NET expects its URLs exactly as written, e.g. "?blp=A1200101&1238653"
        url = URL(base_url + request.path, encoded=True)
        try:
            async with session.request(
                request.method,
                url,
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
    return await run_async(probe(), _performer(session, _with_scheme(ip), timeout))


class WebClient:
    """The web interface of the BL-NET, see pyblnet.sync.WebClient"""

    _def_password = "0128"  # default password is 0128

    def __init__(self, ip, session, password=_def_password, timeout=5):
        """Doesn't check the address, use create() for that"""
        assert isinstance(ip, str)
        assert password is None or isinstance(password, str)
        assert timeout is None or isinstance(timeout, int)
        self.ip = _with_scheme(ip)
        self.protocol = WebProtocol(password)
        self._perform = _performer(session, self.ip, timeout)

    @classmethod
    async def create(cls, ip, session, password=_def_password, timeout=5):
        """Raises ValueError if no BL-NET answers under ip"""
        web = cls(ip, session, password, timeout)
        if not await run_async(probe(), web._perform):
            raise ValueError("No BLNET found under given address: {}".format(web.ip))
        return web

    async def _run(self, flow):
        return await run_async(flow, self._perform)

    async def __aenter__(self):
        await self.log_in()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.log_out()

    async def logged_in(self):
        return await self._run(self.protocol.logged_in())

    async def log_in(self):
        return await self._run(self.protocol.log_in())

    async def log_out(self):
        return await self._run(self.protocol.log_out())

    async def set_node(self, node):
        return await self._run(self.protocol.set_node(node))

    async def read_analog_values(self):
        return await self._run(self.protocol.read_analog_values())

    async def read_digital_values(self):
        return await self._run(self.protocol.read_digital_values())

    async def set_digital_value(self, digital_id, value):
        return await self._run(self.protocol.set_digital_value(digital_id, value))

    async def fetch(self, node=None):
        return await self._run(self.protocol.fetch(node))

    async def turn(self, digital_id, value, node=None):
        return await self._run(self.protocol.turn(digital_id, value, node))
