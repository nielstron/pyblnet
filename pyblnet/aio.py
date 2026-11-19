"""
Async clients for the BL-NET, with the API of the blocking ones, but
awaitable methods and no I/O in the constructors: use the create()
class methods to connect and check the BL-NET like the constructors of
pyblnet.BLNET, BLNETWeb and BLNETDirect do.

Needs aiohttp: pip install pyblnet[async]

    async with aiohttp.ClientSession() as session:
        blnet = await BLNET.create("192.168.1.10", session=session, password="0128")
        data = await blnet.fetch()
        await blnet.turn_on(1)

The web interface tracks the login by a cookie, which pyblnet sends itself.
Pass a session that doesn't share its cookies with other BL-NETs.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from urllib.parse import urlparse

import aiohttp
from yarl import URL

from .direct_protocol import (
    INVALID_REPLY_ERRORS,
    MAX_RETRYS,
    Connect,
    DirectProtocol,
    Disconnect,
    Receive,
    Send,
    Sleep,
)
from .flow import run_async
from .values import add_direct, add_web, empty_data, find_value
from .web_protocol import Response, TransportError, WebSession, probe

__all__ = ["BLNET", "BLNETDirect", "BLNETWeb", "blnet_test"]


def _with_scheme(ip):
    if not ip.startswith("http://") and not ip.startswith("https://"):
        ip = "http://" + ip
    return ip


def _performer(session, base_url, timeout):
    """Perform the requests of web_protocol flows on base_url with aiohttp"""
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


class BLNETWeb:
    """The web interface of the BL-NET, see pyblnet.BLNETWeb"""

    _def_password = "0128"  # default password is 0128

    def __init__(self, ip, session, password=_def_password, timeout=5):
        """Doesn't check the address, use create() for that"""
        assert isinstance(ip, str)
        assert password is None or isinstance(password, str)
        assert timeout is None or isinstance(timeout, int)
        self.ip = _with_scheme(ip)
        self.session = WebSession(password)
        self._perform = _performer(session, self.ip, timeout)

    @classmethod
    async def create(cls, ip, session, password=_def_password, timeout=5):
        """Raises ValueError if no BL-NET answers under ip"""
        blnet_web = cls(ip, session, password, timeout)
        if not await run_async(probe(), blnet_web._perform):
            raise ValueError("No BLNET found under given address: {}".format(blnet_web.ip))
        return blnet_web

    async def _run(self, flow):
        return await run_async(flow, self._perform)

    async def __aenter__(self):
        await self.log_in()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.log_out()

    async def logged_in(self):
        return await self._run(self.session.logged_in())

    async def log_in(self):
        return await self._run(self.session.log_in())

    async def log_out(self):
        return await self._run(self.session.log_out())

    async def set_node(self, node):
        return await self._run(self.session.set_node(node))

    async def read_analog_values(self):
        return await self._run(self.session.read_analog_values())

    async def read_digital_values(self):
        return await self._run(self.session.read_digital_values())

    async def set_digital_value(self, digital_id, value):
        return await self._run(self.session.set_digital_value(digital_id, value))

    async def fetch(self, node=None):
        return await self._run(self.session.fetch(node))

    async def turn(self, digital_id, value, node=None):
        return await self._run(self.session.turn(digital_id, value, node))


class BLNETDirect:
    """The direct connection (TA port) of the BL-NET, see pyblnet.BLNETDirect"""

    def __init__(self, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        """Doesn't connect, use create() for that"""
        assert isinstance(address, str)
        assert isinstance(port, int)
        assert isinstance(reset, bool)
        self.address = address
        self.port = port
        self.reset = reset
        self._timeout = timeout or None
        self._reader = None
        self._writer = None
        self.protocol = DirectProtocol(reset)

    @classmethod
    async def create(cls, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        """Raises ConnectionError if the BL-NET mode is not supported"""
        blnet_direct = cls(address, port, reset, timeout)
        await blnet_direct._run(blnet_direct.protocol.check_mode())
        return blnet_direct

    async def _run(self, flow):
        """
        Run a flow of the protocol. If it fails, close the connection and
        forget the read state, so that the next call starts afresh.
        Malformed replies are raised as ConnectionError.
        """
        try:
            return await run_async(flow, self._perform)
        except INVALID_REPLY_ERRORS as ex:
            await self.close()
            raise ConnectionError(f"Invalid reply from BL-Net: {ex}") from ex
        except BaseException:
            await self.close()
            raise

    async def _perform(self, operation):
        if isinstance(operation, Sleep):
            await asyncio.sleep(operation.seconds)
        elif isinstance(operation, Disconnect):
            await self._disconnect()
        else:
            return await asyncio.wait_for(self._perform_io(operation), self._timeout)

    async def _perform_io(self, operation):
        if isinstance(operation, Send):
            self._writer.write(operation.data)
            await self._writer.drain()
        elif isinstance(operation, Receive):
            return await self._reader.read(operation.max_size)
        elif isinstance(operation, Connect):
            if self._writer is None:
                try:
                    self._reader, self._writer = await asyncio.open_connection(
                        self.address, self.port
                    )
                except OSError as err:
                    raise ConnectionError("Could not connect to BLNET") from err
        else:
            raise TypeError(f"Unknown operation {operation}")

    async def _disconnect(self):
        writer, self._reader, self._writer = self._writer, None, None
        if writer is not None:
            writer.close()
            with suppress(OSError):
                await writer.wait_closed()

    async def close(self):
        """Close the connection if open and forget the read state"""
        await self._disconnect()
        self.protocol.forget()

    async def get_count(self):
        return await self._run(self.protocol.get_count())

    async def get_data(self, max_count=None):
        """The datasets logged in the bootloader memory, up to max_count"""
        return await self._run(self.protocol.get_data(max_count))

    async def get_latest(self, max_retries=MAX_RETRYS):
        return await self._run(self.protocol.get_latest(max_retries))


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
