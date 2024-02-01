# PyBLNET - a very basic python BL-NET bridge
[![Build Status](https://app.travis-ci.com/nielstron/pyblnet.svg?branch=master)](https://app.travis-ci.com/github/nielstron/pyblnet)
[![Coverage Status](https://coveralls.io/repos/github/nielstron/pyblnet/badge.svg?branch=master)](https://coveralls.io/github/nielstron/pyblnet?branch=master)

A package that connects to the BL-NET that is connected itself to a UVR1611 device by Technische Alternative. 
It is able to read digital and analog values as well as to set switches to ON/OFF/AUTO.

Documentation on the modules and their methods can be found with the methods and modules themselves.

Two interfaces to BLNet exist and both are supported:
- Webinterface  - Class BLnetWeb
- BLNet-Direct protocol [1] - Class BLNETDirect

However, as of now, there is no testing on the BLNet-Direct protocol *of any kind*, so enabling it is discouraged until the interface is fixed.
Parsing the data via the web interface is the preferred way of accessing the BLNet for now.

The class BLNET is a wrapper around the two classes. When initializing the class, the two interfaces can be activated/deactivated. 
BLNetDirect provides 'analog', 'digital',  'speed', 'energy', 'power', whereas BLnetWeb supports 'analog' and 'digital' only.
If both are active, BLNetDirect has priority.
Setting switches and reading their manual/auto state is only possible via the BLNetWeb interface.

### Usage

```python
from pyblnet import test_blnet, BLNET, BLNETWeb, BLNETDirect

ip = '192.168.178.10'

# Check if there is a blnet at given address
test_blnet(ip) # -> True/False

# Convenient high level interface
blnet = BLNET(ip, password='pass', timeout=5)

# Control a switch by its ID
blnet.turn_on(10)
blnet.turn_auto(10)
blnet.turn_off(10)

# Fetch data (contains all available data using enabled interfaces)
print(blnet.fetch())



# The low level modules are also available
# note that the direct use of these modules is discouraged though

# Fetch the latest data via web interface
# Note that manual log in and log out are required
# when not using the with statement
with BLNETWeb(ip, password='pass', timeout=5) as blnet_session:
    print(blnet_session.read_analog_values())
    print(blnet_session.read_digital_values())

    # For publishing values
    blnet_session.set_digital_value('10', 'AUS')
    # Note that without explicit log out,
    # the BLNET will block any further web access for the next 150s
    # this is handled automatically when using the with statement

# Fetch data via the Protocol developed by TA
blnet = BLNETDirect(ip)
# Fetching the latest data
print(blnet.get_latest())
# Still inofficial because unexplicably failing often
print(blnet._get_data(1))
```


[1] https://www.haus-terra.at/heizung/download/Schnittstelle/Schnittstelle_PC_Bootloader.pdf
