"""Parsing of saved BL-NET web pages, independent of the mock HTTP server"""

import unittest
from pathlib import Path
from unittest import mock

from pyblnet import BLNETWeb, blnet_test

PAGES = Path(__file__).parent / "test_structure"


def page(name):
    """Response serving a saved page, decoded like requests does for the BL-NET"""
    return mock.Mock(text=(PAGES / name).read_bytes().decode("latin-1"))


def serve(name):
    return mock.patch("pyblnet.blnet_web.requests.get", return_value=page(name))


class BLNETWebPagesTest(unittest.TestCase):
    def setUp(self):
        with serve("main.htm"):
            self.web = BLNETWeb("blnet", password=None)

    def test_blnet_test_recognizes_main_page(self):
        with serve("main.htm"):
            self.assertTrue(blnet_test("blnet"))

    def test_blnet_test_recognizes_access_denied_page(self):
        with serve(".error.html"):
            self.assertTrue(blnet_test("blnet"))

    def test_blnet_test_rejects_other_pages(self):
        with serve("580500.htm"):
            self.assertFalse(blnet_test("blnet"))

    def test_read_analog_values_with_negative_value(self):
        with serve("580500.alternative.htm"):
            values = self.web.read_analog_values()
        self.assertEqual(
            values,
            [
                {"id": "1", "name": "TKollektor", "value": "-0.1", "unit_of_measurement": "°C"},
                {"id": "2", "name": "TSP.oben", "value": "47.1", "unit_of_measurement": "°C"},
                {"id": "3", "name": "TSP.unten", "value": "57.8", "unit_of_measurement": "°C"},
                {"id": "4", "name": "THeizkr.VL", "value": "45.8", "unit_of_measurement": "°C"},
                {"id": "5", "name": "Temp.Aussen", "value": "1.1", "unit_of_measurement": "°C"},
                {"id": "6", "name": "Temp.Raum", "value": "24.1", "unit_of_measurement": "°C"},
                {"id": "7", "name": "T Kaminofen", "value": "55.8", "unit_of_measurement": "°C"},
                {"id": "9", "name": "TZirku.RL", "value": "22.4", "unit_of_measurement": "°C"},
            ],
        )

    def test_read_analog_values_access_denied(self):
        with serve(".error.html"):
            self.assertIsNone(self.web.read_analog_values())

    def test_read_digital_values_access_denied(self):
        with serve(".error.html"):
            self.assertIsNone(self.web.read_digital_values())
