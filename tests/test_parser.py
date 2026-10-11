import struct
from pyblnet.blnet_parser import BLNETParser
import unittest


class TestParser(unittest.TestCase):

    def test_parser_ok(self):
        data = b'} \xb5"f"\x03"~!\x8e"\x16!\xe0 \xff \xf3 \xf8 \x00\x00=!\x01\x00\x00`\xe2!\x00\x00\x80\x00\x00\x00\x00,\x00\xa4(\x06\x00DhI\x82\x1d\x04Ce\xc0\x00'
        parser = BLNETParser(data)
        parsed_values = parser.to_dict()
        expected_values = {
            'analog': {1: 12.5, 2: 69.3, 3: 61.4, 4: 51.5, 5: 38.2, 6: 65.4, 7: 27.8, 8: 22.4, 9: 25.5, 10: 24.3, 11: 24.8, 12: None, 13: 31.7, 14: None, 15: 0, 16: 48.2},
            'digital': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0},
            'speed': {1: None, 2: 0, 3: 0, 4: 0},
            'energy': {1: None, 2: None},
            'power': {1: None, 2: None}
        }

        assert parsed_values['analog'] == expected_values['analog']
        assert parsed_values['digital'] == expected_values['digital']
        assert parsed_values['speed'] == expected_values['speed']
        assert parsed_values['energy'] == expected_values['energy']
        assert parsed_values['power'] == expected_values['power']

    def test_parser_unused_inputs_are_none(self):
        # Input type bits 000 mean "Eingang unbenutzt", regardless of the other bits
        inputs = [0x0000, 0x0001, 0x8005] + [0x2000] * 13
        data = struct.pack('<16H', *inputs) + bytes(55 - 32)
        parsed_values = BLNETParser(data).to_dict()

        assert parsed_values['analog'][1] is None
        assert parsed_values['analog'][2] is None
        assert parsed_values['analog'][3] is None
        assert parsed_values['analog'][4] == 0

    def test_parser_disconnected_temperature_sensor_is_none(self):
        # A temperature input without sensor reads all value bits set (409.5 °C)
        inputs = [0x2FFF, 0x2FFE] + [0x2000] * 14
        data = struct.pack('<16H', *inputs) + bytes(55 - 32)
        parsed_values = BLNETParser(data).to_dict()

        assert parsed_values['analog'][1] is None
        assert parsed_values['analog'][2] == 409.4

    def test_parser_input_types(self):
        # temperature, volume flow, radiation, digital, unused, room sensor, undocumented type 101
        inputs = [0x2000, 0x3000, 0x4000, 0x1000, 0x0000, 0x7000, 0x5000] + [0x2000] * 9
        data = struct.pack('<16H', *inputs) + bytes(55 - 32)
        parsed_values = BLNETParser(data).to_dict()

        expected_types = {1: 'temperature', 2: 'volume_flow', 3: 'radiation', 4: 'digital', 5: None, 6: 'temperature', 7: None}
        expected_types.update({channel: 'temperature' for channel in range(8, 17)})
        assert parsed_values['analog_types'] == expected_types

    def test_parser_heat_meter_1_active(self):
        # Latest data of a real UVR1611 in DL mode (header and checksum stripped),
        # only heat meter 1 is active (active byte = 0x01)
        data = bytes.fromhex(
            'ff2fff2fff2fff2fff2f1b224d210522e92110216e2032210322'
            '6f21ff2f00306102'
            '18000a12'
            '01'
            '000000001a216a01'
            '0b010a3c0001000c'
        )
        parsed_values = BLNETParser(data).to_dict()

        assert parsed_values['energy'] == {1: 362847.4, 2: None}
        assert parsed_values['power'] == {1: 0, 2: None}

    def test_parser_not_ok(self):
        data = b'broken} \xb5"f"\x03"~!\x8e"\x16!\xe0 \xff \xf3 \xf8 \x00\x00=!\x01\x00\x00`\xe2!\x00\x00\x80\x00\x00\x00\x00,\x00\xa4(\x06\x00DhI\x82\x1d\x04Ce\xc0\x00'
        with self.assertRaises(ValueError):
            parser = BLNETParser(data)
