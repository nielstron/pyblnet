#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gc
import socket
import threading
import time
import unittest
import warnings
from unittest import mock

from pyblnet import BLNET, BLNETDirect
from tests.test_structure.blnet_direct_mock_server import (
    BLNETDirectServer,
    DL_LATEST_RESPONSE,
    GET_HEADER,
    GET_LATEST,
    READ_DATA,
    WAIT_RESPONSE,
)

ADDRESS = "localhost"


class BLNETDirectOnlyTest(unittest.TestCase):
    """Test the high level interface with only the direct (DL mode) connection enabled"""

    def setUp(self):
        self.server = BLNETDirectServer((ADDRESS, 0))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def blnet(self, max_retries=5, timeout=5):
        return BLNET(
            ADDRESS,
            ta_port=self.port,
            timeout=timeout,
            use_web=False,
            use_ta=True,
            max_retries=max_retries,
        )

    def test_fetch(self):
        data = self.blnet().fetch()
        self.assertEqual(
            data["analog"][6],
            {"value": 53.9, "type": "temperature", "unit_of_measurement": "°C"},
        )
        self.assertEqual(
            data["analog"][16],
            {"value": 0, "type": "volume_flow", "unit_of_measurement": "l/h"},
        )
        self.assertEqual(data["digital"][1], {"value": 1})
        # speed level 0-30, no unit
        self.assertEqual(data["speed"][1], {"value": 24, "unit_of_measurement": None})
        self.assertEqual(data["energy"], {1: {"value": 362847.4, "unit_of_measurement": "kWh"}})
        self.assertEqual(data["power"], {1: {"value": 0.0, "unit_of_measurement": "kW"}})

    def test_get_value_by_id(self):
        value, entry, _ = self.blnet().get_analog_value(id=6)
        self.assertEqual(value, 53.9)
        self.assertEqual(entry["value"], 53.9)

    def test_fetch_succeeds_on_last_retry(self):
        self.server.latest_responses = [WAIT_RESPONSE, WAIT_RESPONSE, DL_LATEST_RESPONSE]
        data = self.blnet(max_retries=3).fetch()
        self.assertEqual(data["analog"][6]["value"], 53.9)

    def test_fetch_reads_replies_split_into_segments(self):
        self.server.split_latest = True
        blnet = self.blnet()
        for _ in range(3):
            data = blnet.fetch()
            self.assertEqual(data["analog"][6]["value"], 53.9)
            self.assertEqual(data["energy"][1]["value"], 362847.4)

    def test_fetch_reconnects_after_invalid_reply(self):
        # a stray byte ahead of the reply must not shift the following replies
        self.server.latest_responses = [b"\x00" + DL_LATEST_RESPONSE, DL_LATEST_RESPONSE]
        data = self.blnet().fetch()
        self.assertEqual(data["analog"][6]["value"], 53.9)
        self.assertEqual(data["energy"][1]["value"], 362847.4)

    def test_timeout_does_not_change_global_socket_timeout(self):
        BLNETDirect(ADDRESS, self.port, timeout=7)
        self.assertIsNone(socket.getdefaulttimeout())

    def test_failed_connection_attempt_closes_socket(self):
        # Port that refuses connections: bind it, then free it again
        with socket.socket() as s:
            s.bind((ADDRESS, 0))
            refused_port = s.getsockname()[1]
        # The first address refuses the connection, the second one is the BL-NET
        addresses = [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", port))
            for port in (refused_port, self.port)
        ]
        with mock.patch("pyblnet.sync.direct.getaddrinfo", return_value=addresses):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                BLNETDirect(ADDRESS, self.port, timeout=7)
                gc.collect()
        self.assertEqual([w for w in caught if w.category is ResourceWarning], [])

    def test_timeout_is_used_for_direct_connection(self):
        self.server.silent = True
        start = time.monotonic()
        with self.assertRaises(socket.timeout):
            BLNET(ADDRESS, ta_port=self.port, timeout=1, use_web=False, use_ta=True)
        self.assertLess(time.monotonic() - start, 5)

    def test_fetch_recovers_after_timeout(self):
        blnet = self.blnet(timeout=1)
        self.server.silent = True
        with self.assertRaises(socket.timeout):
            blnet.fetch()
        # BL-NET answers again, but the old connection is gone
        self.server.silent = False
        self.server.drop_connections()
        self.assertEqual(blnet.fetch()["analog"][6]["value"], 53.9)

    def test_fetch_raises_connection_error_when_blnet_hangs_up(self):
        blnet = self.blnet(timeout=1)
        self.server.close_on = GET_HEADER
        with self.assertRaises(ConnectionError):
            blnet.fetch()

    def test_fetch_recovers_after_blnet_hung_up(self):
        blnet = self.blnet(timeout=1)
        self.server.close_on = GET_LATEST
        with self.assertRaises(ConnectionError):
            blnet.fetch()
        self.server.close_on = None
        self.assertEqual(blnet.fetch()["analog"][6]["value"], 53.9)

    def test_constructor_closes_socket_on_timeout(self):
        self.server.silent = True
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            with self.assertRaises(socket.timeout):
                BLNETDirect(ADDRESS, self.port, timeout=1)
            gc.collect()
        self.assertEqual([w for w in caught if w.category is ResourceWarning], [])

    def test_read_logged_data_raises_when_blnet_hangs_up(self):
        blnet_direct = BLNETDirect(ADDRESS, self.port, timeout=1)
        self.server.close_on = READ_DATA
        with self.assertRaises(ConnectionError):
            blnet_direct._get_data(1)

    def test_read_logged_data_raises_on_invalid_reply(self):
        blnet_direct = BLNETDirect(ADDRESS, self.port, timeout=1)
        with self.assertRaises(ConnectionError):
            blnet_direct._get_data(1)

    def test_fetch_waits_while_blnet_has_no_new_data(self):
        # Real BL-NETs answer "no data" for up to a few seconds after a read
        blnet = self.blnet(max_retries=3)
        self.server.no_data_until = time.monotonic() + 1
        self.assertEqual(blnet.fetch()["analog"][6]["value"], 53.9)

    def test_fetch_raises_when_blnet_keeps_waiting(self):
        self.server.latest_responses = [WAIT_RESPONSE]
        with self.assertRaises(ConnectionError):
            self.blnet(max_retries=3).fetch()
