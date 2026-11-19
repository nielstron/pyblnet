# PyBLNET - a very basic python BL-NET bridge
[![PyPI - Version](https://img.shields.io/pypi/v/pyblnet)](https://pypi.org/project/PyBLNET/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyblnet)](https://pypi.org/project/PyBLNET/)
[![Build status](https://github.com/PyBLNET/pyblnet/actions/workflows/build.yml/badge.svg)](https://github.com/PyBLNET/pyblnet/actions/workflows/build.yml)
[![Coverage Status](https://coveralls.io/repos/github/PyBLNET/pyblnet/badge.svg?branch=master)](https://coveralls.io/github/PyBLNET/pyblnet?branch=master)

A package that connects to the BL-NET that is connected itself to a UVR1611 device by Technische Alternative.
It is able to read digital and analog values as well as to set switches to ON/OFF/AUTO.

Documentation on the modules and their methods can be found with the methods and modules themselves.

## Installation

```
pip install pyblnet          # blocking clients
pip install pyblnet[async]   # also the async clients, with aiohttp
```

## Interfaces

The BL-NET has two interfaces, and pyblnet has a client for each:

- `web.Client`: the web interface. Reads 'analog' and 'digital' values with their names, and sets switches.
- `direct.Client`: the direct connection (BLNet-Direct protocol [1], TA port).
  Reads 'analog', 'digital', 'speed', 'energy' and 'power' values, without names.
  It is only tested against a simulated BL-NET, the web interface is the preferred way of accessing it.

`Client` combines both, each can be enabled or disabled with `use_web` and `use_ta`.
If both are enabled, values of the direct connection have priority.
Setting switches and reading their manual/auto state is only possible via the web interface.


## Blocking usage

### Client

```python
from pyblnet import Client  # the same as pyblnet.sync.Client

blnet = Client.create('192.168.178.10', password='pass', timeout=5)

# Fetch all data available via the enabled interfaces
print(blnet.fetch())

# Get a value by its name or id
value, entry, data = blnet.get_analog_value(name='TSP.oben')

# Control a switch by its id
blnet.turn_on(10)
blnet.turn_off(10)
blnet.turn_auto(10)
```

### Web interface

```python
from pyblnet.sync import web

# Check if there is a BL-NET at the given address
web.Client.probe('192.168.178.10')  # -> True/False

# The with statement logs in and out. Without logging out,
# the BL-NET blocks any further web access for the next 150s.
with web.Client.create('192.168.178.10', password='pass', timeout=5) as client:
    print(client.read_analog_values())
    print(client.read_digital_values())
    client.set_digital_value(10, 'AUS')
```

### Direct connection

```python
from pyblnet.sync import direct

client = direct.Client.create('192.168.178.10')
print(client.get_latest())
# Logged data, still inofficial because it fails often
print(client.get_data(1))
```

## Async usage

The async clients need an `aiohttp` session for the web interface, and are closed with `close()`
if they use the direct connection.

### Client

```python
import asyncio
import aiohttp
from pyblnet import aio

async def main():
    async with aiohttp.ClientSession() as session:
        blnet = await aio.Client.create('192.168.178.10', session, password='pass', timeout=5)
        print(await blnet.fetch())
        await blnet.turn_auto(10)

asyncio.run(main())
```

### Web interface

```python
async def main():
    async with aiohttp.ClientSession() as session:
        print(await aio.web.Client.probe('192.168.178.10', session))  # -> True/False
        client = await aio.web.Client.create('192.168.178.10', session, password='pass')
        async with client:
            print(await client.read_analog_values())
            await client.set_digital_value(10, 'AUS')
```

### Direct connection

```python
async def main():
    client = await aio.direct.Client.create('192.168.178.10')
    try:
        print(await client.get_latest())
    finally:
        await client.close()
```

[1] Technische Alternative, "Schnittstelle Winsol <> Bootloader" (2006), archived copy: http://web.archive.org/web/20160122124754/http://www.haus-terra.at:80/heizung/download/Schnittstelle/Schnittstelle_PC_Bootloader.pdf
