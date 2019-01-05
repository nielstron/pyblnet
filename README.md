# PyBLNET - a very basic python BL-NET bridge
[![Build Status](https://travis-ci.com/nielstron/pyblnet.svg?branch=master)](https://travis-ci.com/nielstron/pyblnet)
[![Coverage Status](https://coveralls.io/repos/github/nielstron/pyblnet/badge.svg?branch=master)](https://coveralls.io/github/nielstron/pyblnet?branch=master)

A package that connects to the BL-NET that is connected itself to a UVR1611 device by Technische Alternative. 
It is able to read digital and analog values as well as to set switches to ON/OFF/AUTO

```python
ip = '192.168.178.10'

# Check if there is a blnet at given address
print(test_blnet(ip))

# Easy to use high level interface
blnet = BLNET(ip, timeout=5)
print(blnet.turn_on(10))
print(blnet.fetch())

# Fetch the latest data via web interface
blnet = BLNETWeb(ip, timeout=5)
print(blnet.read_analog_values())
print(blnet.read_digital_values())

# For publishing values
#print(blnet.set_digital_value("10", 'AUS'))
#print(blnet.read_digital_values())

blnet = BLNETDirect(ip)
# Fetching the latest data from the backend
print(blnet.get_latest())
# Still inofficial because unexplicably failing often
print(blnet._get_data(1))
```
