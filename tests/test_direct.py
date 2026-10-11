#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import threading
import unittest

from pyblnet import BLNET, BLNETDirect
from tests.test_structure.blnet_direct_mock_server import (
    BLNETDirectServer,
    DL_LATEST_RESPONSE,
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

    def blnet(self, max_retries=5):
        return BLNET(
            ADDRESS,
            ta_port=self.port,
            use_web=False,
            use_ta=True,
            max_retries=max_retries,
        )

    def test_fetch(self):
        data = self.blnet().fetch()
        self.assertEqual(data["analog"][6], {"value": 53.9})
        self.assertEqual(data["digital"][1], {"value": 1})
        self.assertEqual(data["speed"][1], {"value": 24})
        self.assertEqual(data["energy"], {1: {"value": 362847.4}})

    def test_get_value_by_id(self):
        value, entry, _ = self.blnet().get_analog_value(id=6)
        self.assertEqual(value, 53.9)
        self.assertEqual(entry, {"value": 53.9})

    def test_fetch_succeeds_on_last_retry(self):
        self.server.latest_responses = [WAIT_RESPONSE, WAIT_RESPONSE, DL_LATEST_RESPONSE]
        data = self.blnet(max_retries=3).fetch()
        self.assertEqual(data["analog"][6], {"value": 53.9})

    def test_timeout_does_not_change_global_socket_timeout(self):
        BLNETDirect(ADDRESS, self.port, timeout=7)
        self.assertIsNone(socket.getdefaulttimeout())

    def test_fetch_raises_when_blnet_keeps_waiting(self):
        self.server.latest_responses = [WAIT_RESPONSE]
        with self.assertRaises(ConnectionError):
            self.blnet(max_retries=3).fetch()
