STATE = {
    "analog": {
        1: {
            "id": "1",
            "name": "TKollektor",
            "unit_of_measurement": "°C",
            "value": "5.3",
        },
        2: {
            "id": "2",
            "name": "TSP.oben",
            "unit_of_measurement": "°C",
            "value": "46.3",
        },
        3: {
            "id": "3",
            "name": "TSP.unten",
            "unit_of_measurement": "°C",
            "value": "53.1",
        },
        4: {
            "id": "4",
            "name": "THeizkr.VL",
            "unit_of_measurement": "°C",
            "value": "44.8",
        },
        5: {
            "id": "5",
            "name": "Temp.Aussen",
            "unit_of_measurement": "°C",
            "value": "-72.3",
        },
        6: {
            "id": "6",
            "name": "Temp.Raum",
            "unit_of_measurement": "°C",
            "value": "24.6",
        },
        7: {
            "id": "7",
            "name": "T Kaminofen",
            "unit_of_measurement": "°C",
            "value": "20.9",
        },
        9: {
            "id": "9",
            "name": "TZirku.RL",
            "unit_of_measurement": "°C",
            "value": "36.6",
        },
    },
    "digital": {
        1: {"id": "1", "mode": "AUTO", "name": "Pumpe-Solar", "value": "AUS"},
        2: {"id": "2", "mode": "AUTO", "name": "Pumpe-Hzkr", "value": "EIN"},
        5: {"id": "5", "mode": "AUTO", "name": "Anf.Kessel", "value": "AUS"},
        6: {"id": "6", "mode": "HAND", "name": "Vent.Solar", "value": "AUS"},
        7: {"id": "7", "mode": "AUTO", "name": "P Kaminofen", "value": "EIN"},
        10: {"id": "10", "mode": "HAND", "name": "WW-Pumpe1", "value": "AUS"},
    },
    "energy": {},
    "power": {},
    "speed": {},
}

STATE_ALTERNATIVE = {
    "analog": {
        2: {
            "id": "2",
            "name": "TSP.oben",
            "value": "47.1",
            "unit_of_measurement": "°C",
        },
        3: {
            "id": "3",
            "name": "TSP.unten",
            "value": "57.8",
            "unit_of_measurement": "°C",
        },
        4: {
            "id": "4",
            "name": "THeizkr.VL",
            "value": "45.8",
            "unit_of_measurement": "°C",
        },
        5: {
            "id": "5",
            "name": "Temp.Aussen",
            "value": "1.1",
            "unit_of_measurement": "°C",
        },
        6: {
            "id": "6",
            "name": "Temp.Raum",
            "value": "24.1",
            "unit_of_measurement": "°C",
        },
        7: {
            "id": "7",
            "name": "T Kaminofen",
            "value": "55.8",
            "unit_of_measurement": "°C",
        },
        9: {
            "id": "9",
            "name": "TZirku.RL",
            "value": "22.4",
            "unit_of_measurement": "°C",
        },
    },
    "digital": {
        1: {"id": "1", "name": "Pumpe-Solar", "mode": "AUTO", "value": "AUS"},
        2: {"id": "2", "name": "Pumpe-Hzkr", "mode": "AUTO", "value": "EIN"},
        5: {"id": "5", "name": "Anf.Kessel", "mode": "AUTO", "value": "AUS"},
        6: {"id": "6", "name": "Vent.Solar", "mode": "HAND", "value": "AUS"},
        7: {"id": "7", "name": "P Kaminofen", "mode": "AUTO", "value": "EIN"},
        10: {"id": "10", "name": "WW-Pumpe1", "mode": "HAND", "value": "AUS"},
    },
    "speed": {},
    "energy": {},
    "power": {},
}

STATE_ANALOG = [
    {"id": "1", "name": "TKollektor", "unit_of_measurement": "°C", "value": "5.3"},
    {"id": "2", "name": "TSP.oben", "unit_of_measurement": "°C", "value": "46.3"},
    {"id": "3", "name": "TSP.unten", "unit_of_measurement": "°C", "value": "53.1"},
    {"id": "4", "name": "THeizkr.VL", "unit_of_measurement": "°C", "value": "44.8"},
    {"id": "5", "name": "Temp.Aussen", "unit_of_measurement": "°C", "value": "-72.3"},
    {"id": "6", "name": "Temp.Raum", "unit_of_measurement": "°C", "value": "24.6"},
    {"id": "7", "name": "T Kaminofen", "unit_of_measurement": "°C", "value": "20.9"},
    {"id": "9", "name": "TZirku.RL", "unit_of_measurement": "°C", "value": "36.6"},
]

STATE_ANALOG_ALTERNATIVE = [
    {"id": "2", "name": "TSP.oben", "unit_of_measurement": "°C", "value": "47.1"},
    {"id": "3", "name": "TSP.unten", "unit_of_measurement": "°C", "value": "57.8"},
    {"id": "4", "name": "THeizkr.VL", "unit_of_measurement": "°C", "value": "45.8"},
    {"id": "5", "name": "Temp.Aussen", "unit_of_measurement": "°C", "value": "1.1"},
    {"id": "6", "name": "Temp.Raum", "unit_of_measurement": "°C", "value": "24.1"},
    {"id": "7", "name": "T Kaminofen", "unit_of_measurement": "°C", "value": "55.8"},
    {"id": "9", "name": "TZirku.RL", "unit_of_measurement": "°C", "value": "22.4"},
]

STATE_DIGITAL = [
    {"id": "1", "mode": "AUTO", "name": "Pumpe-Solar", "value": "AUS"},
    {"id": "2", "mode": "AUTO", "name": "Pumpe-Hzkr", "value": "EIN"},
    {"id": "5", "mode": "AUTO", "name": "Anf.Kessel", "value": "AUS"},
    {"id": "6", "mode": "HAND", "name": "Vent.Solar", "value": "AUS"},
    {"id": "7", "mode": "AUTO", "name": "P Kaminofen", "value": "EIN"},
    {"id": "10", "mode": "HAND", "name": "WW-Pumpe1", "value": "AUS"},
]
