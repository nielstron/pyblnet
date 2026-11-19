"""Parsing of saved BL-NET web pages, independent of the mock HTTP server"""

import struct
import unittest
from pathlib import Path
from unittest import mock

from pyblnet import Client, blnet_test
from pyblnet.sync import web
from pyblnet.protocol.parser import Parser

PAGES = Path(__file__).parent / "test_structure"


def page(name):
    """Response serving a saved page, decoded like requests does for the BL-NET"""
    return mock.Mock(text=(PAGES / name).read_bytes().decode("latin-1"))


def serve(name):
    return mock.patch("pyblnet.sync.web.requests.get", return_value=page(name))


class WebPagesTest(unittest.TestCase):
    def setUp(self):
        with serve("main.htm"):
            self.web = web.Client("blnet", password=None)

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

    def test_read_analog_values_with_digital_inputs(self):
        # inputs 3, 8, 13 and 14 are digital inputs, shown as AUS/EIN
        with serve("580500.digital_inputs.htm"):
            values = self.web.read_analog_values()
        digital = {"unit_of_measurement": None, "type": "digital"}
        self.assertEqual(
            values,
            [
                {"id": "1", "name": "T.Kollektor", "value": "14.2", "unit_of_measurement": "°C"},
                {"id": "2", "name": "T.WW.Puffer", "value": "62.1", "unit_of_measurement": "°C"},
                {"id": "3", "name": "-----", "value": "0", **digital},
                {"id": "4", "name": "T.Solar-RL", "value": "38.1", "unit_of_measurement": "°C"},
                {"id": "5", "name": "T.Zirku.RL", "value": "22.8", "unit_of_measurement": "°C"},
                {"id": "6", "name": "T.Puffer.m", "value": "62.0", "unit_of_measurement": "°C"},
                {"id": "7", "name": "T.Puffer.o", "value": "62.3", "unit_of_measurement": "°C"},
                {"id": "8", "name": "Freigabe1", "value": "0", **digital},
                {"id": "9", "name": "T.Kessel-VL", "value": "59.3", "unit_of_measurement": "°C"},
                {"id": "10", "name": "T.Heizkr.VL1", "value": "27.0", "unit_of_measurement": "°C"},
                {"id": "11", "name": "T.Heizkr.VL2", "value": "31.6", "unit_of_measurement": "°C"},
                {"id": "12", "name": "Temp.Aussen", "value": "10.4", "unit_of_measurement": "°C"},
                {"id": "13", "name": "Digitaleing.1", "value": "1", **digital},
                {"id": "14", "name": "Digitaleing.2", "value": "1", **digital},
                {"id": "15", "name": "Temp.Raum2", "value": "999.9", "unit_of_measurement": "°C"},
                {"id": "16", "name": "Temp.Raum1", "value": "20.1", "unit_of_measurement": "°C"},
            ],
        )

    def test_fetch_reports_digital_inputs_as_analog_inputs_of_type_digital(self):
        with serve("main.htm"):
            blnet = Client("blnet")
        with serve("580500.digital_inputs.htm"), mock.patch.object(
            web.Client, "read_digital_values", return_value=[]
        ):
            data = blnet.fetch()
        self.assertEqual(data["analog"][8]["type"], "digital")
        self.assertEqual(data["analog"][8]["value"], "0")
        self.assertEqual(data["analog"][1]["type"], "temperature")

    def test_fetch_keeps_web_value_of_digital_input_missing_in_direct_data(self):
        # A UVR1611 on CAN sends digital inputs with type bits 000 (unused)
        # and the state in bit 0, see the recorded dataset in pyblnet-async.
        # The parser reports those as None, the web value has to stay.
        inputs = [0x208F] + [0x2000] * 11 + [0x0001, 0x0001] + [0x2000] * 2
        direct = Parser(struct.pack("<16H", *inputs) + bytes(55 - 32)).to_dict()
        with serve("main.htm"):
            blnet = Client("blnet")
        blnet.direct = mock.Mock(get_latest=mock.Mock(return_value={0: direct}))
        with serve("580500.digital_inputs.htm"), mock.patch.object(
            web.Client, "read_digital_values", return_value=[]
        ):
            data = blnet.fetch()
        self.assertEqual(data["analog"][13]["value"], "1")
        self.assertEqual(data["analog"][1]["value"], 14.3)

    def test_read_digital_values_with_mixer(self):
        # outputs 3 and 4 open and close a mixer, 15 and 16 are analog outputs
        with serve("580600.mixer.htm"):
            values = self.web.read_digital_values()
        self.assertEqual(
            values,
            [
                {"id": "1", "name": "Ladep.WW.", "mode": "AUTO", "value": "AUS"},
                {"id": "2", "name": "Pumpe-Hzkr", "mode": "HAND", "value": "AUS"},
                {"id": "3", "name": "Misch.Hzkr auf", "mode": "AUTO", "value": "AUS"},
                {"id": "4", "name": "Misch.Hzkr zu", "mode": "AUTO", "value": "AUS"},
                {"id": "5", "name": "Anf.Brenner", "mode": "AUTO", "value": "AUS"},
                {"id": "10", "name": "Notheizer", "mode": "HAND", "value": "AUS"},
            ],
        )

    def test_read_analog_values_access_denied(self):
        with serve(".error.html"):
            self.assertIsNone(self.web.read_analog_values())

    def test_read_digital_values_access_denied(self):
        with serve(".error.html"):
            self.assertIsNone(self.web.read_digital_values())
