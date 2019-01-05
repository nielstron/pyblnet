#!/usr/bin/env python
# -*- coding: utf-8 -*-

# general requirements
import unittest
from .server_control import Server
from .blnet_mock_server import BLNETServer, BLNETRequestHandler

# For the server in this case
import time

# For the tests
import requests
from pyblnet import BLNET, test_blnet, BLNETWeb
from .web_raw.web_state import STATE, STATE_ANALOG, STATE_DIGITAL


ADDRESS = 'localhost'
PASSWORD = '0123'


class SetupTest(unittest.TestCase):

    server = None
    server_control = None
    port = 0
    url = 'http://localhost:80'

    def setUp(self):
        # Create an arbitrary subclass of TCP Server as the server to be started
        # Here, it is an Simple HTTP file serving server
        handler = BLNETRequestHandler

        max_retries = 10
        r = 0
        while not self.server:
            try:
                # Connect to any open port
                self.server = BLNETServer((ADDRESS, 0), handler)
            except OSError:
                if r < max_retries:
                    r += 1
                else:
                    raise
                time.sleep(1)

        self.server_control = Server(self.server)
        self.server.set_password(PASSWORD)
        self.port = self.server_control.get_port()
        self.url = "http://{}:{}".format(ADDRESS, self.port)
        # Start test server before running any tests
        self.server_control.start_server()

    def test_blnet(self):
        self.assertTrue(test_blnet(self.url, timeout=10))

    def test_blnet_login(self):
        self.assertTrue(BLNETWeb(self.url, password=PASSWORD, timeout=10).log_in())

    def test_blnet_fetch(self):
        self.assertEqual(
            BLNET(ADDRESS, password=PASSWORD, timeout=10, use_ta=False, web_port=self.port).fetch(),
            STATE
        )

    def test_blnet_web_analog(self):
        self.assertEqual(
            BLNETWeb(self.url, password=PASSWORD, timeout=10).read_analog_values(),
            STATE_ANALOG
        )

    def test_blnet_web_digital(self):
        self.assertEqual(
            BLNETWeb(self.url, password=PASSWORD, timeout=10).read_digital_values(),
            STATE_DIGITAL
        )

    def tearDown(self):
        self.server_control.stop_server()
        pass


if __name__ == "__main__":
    unittest.main()
