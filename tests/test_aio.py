"""
The async clients, against the same mock servers as the blocking ones.
They share the protocol, so they must return the same.
"""
import asyncio
import threading
import unittest

import aiohttp

from pyblnet import Client, aio
from tests.test_structure.blnet_direct_mock_server import (
    BLNETDirectServer,
    DL_LATEST_RESPONSE,
    GET_HEADER,
    GET_LATEST,
    WAIT_RESPONSE,
)
from tests.test_structure.blnet_mock_server import BLNETRequestHandler, BLNETServer, PASSWORD
from tests.test_structure.server_control import Server
from tests.web_raw.web_state import STATE, STATE_ANALOG, STATE_DIGITAL

ADDRESS = "localhost"


class AsyncWebTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.server = BLNETServer((ADDRESS, 0), BLNETRequestHandler)
        self.server_control = Server(self.server)
        self.server.set_password(PASSWORD)
        self.port = self.server_control.get_port()
        self.url = "http://{}:{}".format(ADDRESS, self.port)
        self.server_control.start_server()

    def tearDown(self):
        self.server_control.stop_server()

    async def asyncSetUp(self):
        self.session = aiohttp.ClientSession()

    async def asyncTearDown(self):
        await self.session.close()

    def blnet_kwargs(self, password=PASSWORD):
        return dict(password=password, timeout=10, use_ta=False, web_port=self.port)

    async def test_blnet_test(self):
        self.assertTrue(await aio.blnet_test(self.session, self.url, timeout=10))
        self.server.set_blocked()
        self.assertTrue(await aio.blnet_test(self.session, self.url, timeout=10))

    async def test_blnet_test_offline(self):
        self.server_control.stop_server()
        self.assertFalse(await aio.blnet_test(self.session, self.url, timeout=2))
        with self.assertRaises(ValueError):
            await aio.WebClient.create(self.url, self.session)

    async def test_log_in(self):
        blnet = await aio.WebClient.create(
            "{}:{}".format(ADDRESS, self.port), self.session, password=PASSWORD, timeout=10
        )
        async with blnet:
            self.assertTrue(await blnet.logged_in())
        self.assertFalse(await blnet.logged_in())

    async def test_read_values(self):
        blnet = await aio.WebClient.create(self.url, self.session, password=PASSWORD, timeout=10)
        async with blnet:
            self.assertEqual(await blnet.read_analog_values(), STATE_ANALOG)
            self.assertEqual(await blnet.read_digital_values(), STATE_DIGITAL)
            self.assertTrue(await blnet.set_digital_value(10, "2"))
            self.assertEqual(self.server.get_node("A"), "2")

    async def test_fetch_like_blocking_client(self):
        blnet = await aio.Client.create(ADDRESS, session=self.session, **self.blnet_kwargs())
        fetched = await blnet.fetch()
        self.assertEqual(fetched, STATE)
        blocking = await asyncio.to_thread(lambda: Client(ADDRESS, **self.blnet_kwargs()).fetch())
        self.assertEqual(fetched, blocking)

    async def test_fetch_access_denied_like_blocking_client(self):
        blnet = await aio.Client.create(ADDRESS, session=self.session, **self.blnet_kwargs(None))
        blocking = await asyncio.to_thread(
            lambda: Client(ADDRESS, **self.blnet_kwargs(None)).fetch()
        )
        self.assertEqual(await blnet.fetch(), blocking)

    async def test_get_value(self):
        blnet = await aio.Client.create(ADDRESS, session=self.session, **self.blnet_kwargs())
        value, entry, _ = await blnet.get_value(name="TSP.oben", type="analog")
        self.assertEqual(entry, STATE["analog"][2])
        self.assertEqual(value, STATE["analog"][2]["value"])

    async def test_turn(self):
        blnet = await aio.Client.create(ADDRESS, session=self.session, **self.blnet_kwargs())
        await blnet.turn_on(10)
        self.assertEqual(self.server.get_node("A"), "2")
        await blnet.turn_auto(8)
        self.assertEqual(self.server.get_node("8"), "3")
        await blnet.turn_off(1)
        self.assertEqual(self.server.get_node("1"), "1")

    async def test_turn_fails_without_login(self):
        blnet = await aio.Client.create(ADDRESS, session=self.session, **self.blnet_kwargs("wrong"))
        with self.assertRaises(ConnectionError):
            await blnet.turn_on(10)

    async def test_web_needs_session(self):
        with self.assertRaises(ValueError):
            await aio.Client.create(ADDRESS, **self.blnet_kwargs())


class AsyncDirectTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.server = BLNETDirectServer((ADDRESS, 0))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def kwargs(self, max_retries=5, timeout=5):
        return dict(
            ta_port=self.port, timeout=timeout, use_web=False, use_ta=True, max_retries=max_retries
        )

    async def blnet(self, **kwargs):
        blnet = await aio.Client.create(ADDRESS, **self.kwargs(**kwargs))
        self.addAsyncCleanup(blnet.close)
        return blnet

    async def test_fetch_like_blocking_client(self):
        fetched = await (await self.blnet()).fetch()
        self.assertEqual(
            fetched["analog"][6],
            {"value": 53.9, "type": "temperature", "unit_of_measurement": "°C"},
        )
        self.assertEqual(fetched["speed"][1], {"value": 24, "unit_of_measurement": None})
        blocking = await asyncio.to_thread(lambda: Client(ADDRESS, **self.kwargs()).fetch())
        self.assertEqual(fetched, blocking)

    async def test_fetch_succeeds_on_last_retry(self):
        self.server.latest_responses = [WAIT_RESPONSE, WAIT_RESPONSE, DL_LATEST_RESPONSE]
        data = await (await self.blnet(max_retries=3)).fetch()
        self.assertEqual(data["analog"][6]["value"], 53.9)

    async def test_fetch_raises_when_blnet_keeps_waiting(self):
        self.server.latest_responses = [WAIT_RESPONSE]
        with self.assertRaises(ConnectionError):
            await (await self.blnet(max_retries=3)).fetch()

    async def test_fetch_reads_replies_split_into_segments(self):
        self.server.split_latest = True
        blnet = await self.blnet()
        for _ in range(3):
            self.assertEqual((await blnet.fetch())["energy"][1]["value"], 362847.4)

    async def test_fetch_reconnects_after_invalid_reply(self):
        self.server.latest_responses = [b"\x00" + DL_LATEST_RESPONSE, DL_LATEST_RESPONSE]
        data = await (await self.blnet()).fetch()
        self.assertEqual(data["energy"][1]["value"], 362847.4)

    async def test_fetch_recovers_after_timeout(self):
        blnet = await self.blnet(timeout=1)
        self.server.silent = True
        with self.assertRaises(asyncio.TimeoutError):
            await blnet.fetch()
        self.server.silent = False
        self.server.drop_connections()
        self.assertEqual((await blnet.fetch())["analog"][6]["value"], 53.9)

    async def test_fetch_recovers_after_blnet_hung_up(self):
        blnet = await self.blnet(timeout=1)
        self.server.close_on = GET_LATEST
        with self.assertRaises(ConnectionError):
            await blnet.fetch()
        self.server.close_on = None
        self.assertEqual((await blnet.fetch())["analog"][6]["value"], 53.9)

    async def test_fetch_raises_connection_error_when_blnet_hangs_up(self):
        self.server.close_on = GET_HEADER
        blnet = await self.blnet(timeout=1)
        with self.assertRaises(ConnectionError):
            await blnet.fetch()

    async def test_connection_refused(self):
        self.tearDown()
        with self.assertRaises(ConnectionError):
            await aio.DirectClient.create(ADDRESS, self.port, timeout=1)
        self.setUp()

    async def test_read_logged_data_raises_on_invalid_reply(self):
        direct = await aio.DirectClient.create(ADDRESS, self.port, timeout=1)
        with self.assertRaises(ConnectionError):
            await direct.get_data(1)
