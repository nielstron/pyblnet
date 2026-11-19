"""
Async clients for the BL-NET, with the API of the blocking ones in
pyblnet.sync, but awaitable methods. Like those, they are made with
create(), which checks the BL-NET.

Needs aiohttp: pip install pyblnet[async]

    async with aiohttp.ClientSession() as session:
        blnet = await Client.create("192.168.1.10", session=session, password="0128")
        data = await blnet.fetch()
        await blnet.turn_on(1)

The web interface tracks the login by a cookie, which pyblnet sends itself.
Pass a session that doesn't share its cookies with other BL-NETs.
"""

from .client import Client
from . import direct, web

__all__ = ["Client", "direct", "web"]
