"""
Async clients for the BL-NET, with the API of the blocking ones, but
awaitable methods and no I/O in the constructors: use the create()
class methods to connect and check the BL-NET like the constructors of
pyblnet.BLNET, BLNETWeb and BLNETDirect do.

Needs aiohttp: pip install pyblnet[async]

    async with aiohttp.ClientSession() as session:
        blnet = await BLNET.create("192.168.1.10", session=session, password="0128")
        data = await blnet.fetch()
        await blnet.turn_on(1)

The web interface tracks the login by a cookie, which pyblnet sends itself.
Pass a session that doesn't share its cookies with other BL-NETs.
"""

from .blnet import BLNET
from .direct import BLNETDirect
from .web import BLNETWeb, blnet_test

__all__ = ["BLNET", "BLNETDirect", "BLNETWeb", "blnet_test"]
