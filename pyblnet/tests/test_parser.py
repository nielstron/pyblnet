from pyblnet.blnet_parser import BLNETParser
import unittest


class TestParser(unittest.TestCase):

    def test_parser_ok(self):
        data = b'} \xb5"f"\x03"~!\x8e"\x16!\xe0 \xff \xf3 \xf8 \x00\x00=!\x01\x00\x00`\xe2!\x00\x00\x80\x00\x00\x00\x00,\x00\xa4(\x06\x00DhI\x82\x1d\x04Ce\xc0\x00'
        parser = BLNETParser(data)
        parsed_values = parser.to_dict()
        expected_values = {
            'analog': {1: 12.5, 2: 69.3, 3: 61.4, 4: 51.5, 5: 38.2, 6: 65.4, 7: 27.8, 8: 22.4, 9: 25.5, 10: 24.3, 11: 24.8, 12: 0, 13: 31.7, 14: 1, 15: 0, 16: 48.2},
            'digital': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0},
            'speed': {},
            'energy': {},
            'power': {}
        }

        assert parsed_values == expected_values

    def test_parser_not_ok(self):
        data = b'broken} \xb5"f"\x03"~!\x8e"\x16!\xe0 \xff \xf3 \xf8 \x00\x00=!\x01\x00\x00`\xe2!\x00\x00\x80\x00\x00\x00\x00,\x00\xa4(\x06\x00DhI\x82\x1d\x04Ce\xc0\x00'
        with self.assertRaises(ValueError):
            parser = BLNETParser(data)
