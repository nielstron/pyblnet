#!/usr/bin/env python
# -*- coding: utf-8 -*-

# general requirements
import unittest
from . import server_control

# For the server in this case
import http.server
import socketserver
import time

# For the tests
import requests


ADDRESS = 'localhost'


class SetupTest(unittest.TestCase):

    server_control = None
    port = 0

    def setUp(self):
        # Create an arbitrary subclass of TCP Server as the server to be started
        # Here, it is an Simple HTTP file serving server
        Handler = http.server.SimpleHTTPRequestHandler

        max_retries = 10
        r = 0
        while not self.server_control:
            try:
                # Connect to any open port
                self.server_control = server_control.Server(socketserver.TCPServer((ADDRESS, 0), Handler))
            except OSError:
                if r < max_retries:
                    r += 1
                else:
                    raise
                time.sleep(1)
        self.port = self.server_control.get_port()
        # Start test server before running any tests
        self.server_control.start_server()

    def test_request(self):
        # Simple example server test
        r = requests.get('http://{}:{}'.format(ADDRESS, self.port), timeout=10)
        self.assertEqual(r.status_code, 200)

    def tearDown(self):
        self.server_control.stop_server()
        pass


if __name__ == "__main__":
    unittest.main()
