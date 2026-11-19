"""
Combine what the web interface and the direct connection read into the data
Client.fetch returns, and look values up in it. Shared by pyblnet.sync.Client
and pyblnet.aio.Client.
"""
from .parser import ANALOG_UNITS

# Units of the values only available via the direct connection, speed is a level 0-30
UNITS = {"speed": None, "energy": "kWh", "power": "kW"}
# Analog input type for the units shown by the web interface
WEB_UNIT_TYPES = {unit: input_type for input_type, unit in ANALOG_UNITS.items() if unit is not None}


def empty_data():
    return {"analog": {}, "digital": {}, "speed": {}, "energy": {}, "power": {}}


def convert_web(values):
    """The list read from the web interface as a dict by id"""
    data = {}
    try:
        for sensor in values:
            data[int(sensor["id"])] = sensor
    except TypeError:
        pass
    return data


def add_web(data, analog, digital):
    """Add the analog and digital values read from the web interface"""
    data["analog"] = convert_web(analog)
    data["digital"] = convert_web(digital)
    for entry in data["analog"].values():
        # digital inputs come with their type, others by their unit
        entry.setdefault("type", WEB_UNIT_TYPES.get(entry.get("unit_of_measurement")))


def add_direct(data, direct, use_web):
    """Add the latest values read via the direct connection, of its first frame"""
    # Override values for analog and digital as values are
    # expected to be more precise here
    for domain in ["analog", "digital"]:
        for id, value in direct[domain].items():
            if data[domain].get(id) is not None:
                # Keep the web value if the direct one is missing: a
                # UVR1611 on CAN sends digital inputs as unused inputs
                if value is not None:
                    data[domain][id]["value"] = value
            elif not use_web:
                if value is None:
                    continue
                data[domain][id] = {"value": value}
                if domain == "analog":
                    input_type = direct["analog_types"][id]
                    data[domain][id]["type"] = input_type
                    data[domain][id]["unit_of_measurement"] = ANALOG_UNITS.get(input_type)

    for domain in ["speed", "energy", "power"]:
        for id, value in direct[domain].items():
            if value is None:
                continue
            data[domain][id] = {"value": value, "unit_of_measurement": UNITS[domain]}


def find_value(data, name=None, id=None, type="digital", ret="value"):
    """
    The value (or mode if ret='mode') of the entry with the given name or id,
    and the entry itself
    """
    val = None
    dic = None
    for key, v in data[type].items():
        # values fetched only via the direct connection have no name
        if (name is not None and str(v.get("name")) == str(name)) or (
            id is not None and str(key) == str(id)
        ):
            val = v.get(ret)
            dic = v
    return val, dic
