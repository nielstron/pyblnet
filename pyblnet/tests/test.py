#!/usr/bin/env python
# -*- coding: utf-8 -*-

# general requirements
import unittest
from . import server_control, blnet_mock_server

# For the server in this case
import time

# For the tests
import requests
from pyblnet import BLNET, test_blnet


ADDRESS = 'localhost'


class SetupTest(unittest.TestCase):

    server_control = None
    port = 0
    url = 'http://localhost:80'

    def setUp(self):
        # Create an arbitrary subclass of TCP Server as the server to be started
        # Here, it is an Simple HTTP file serving server
        handler = blnet_mock_server.BLNETRequestHandler

        max_retries = 10
        r = 0
        while not self.server_control:
            try:
                # Connect to any open port
                self.server_control = server_control.Server(blnet_mock_server.BLNETServer((ADDRESS, 0), handler))
            except OSError:
                if r < max_retries:
                    r += 1
                else:
                    raise
                time.sleep(1)
        self.port = self.server_control.get_port()
        self.url = "http://{}:{}".format(ADDRESS, self.port)
        # Start test server before running any tests
        self.server_control.start_server()

    def test_request(self):
        # Simple example server test
        r = requests.get('{}/580500.htm'.format(self.url), timeout=10)
        self.assertEqual(r.status_code, 200)

    def test_blnet(self):
        self.assertTrue(test_blnet(self.url, timeout=10))

    def tearDown(self):
        self.server_control.stop_server()
        pass


if __name__ == "__main__":
    unittest.main()
