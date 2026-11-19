"""The direct connection (TA port) of the BL-NET, with asyncio streams"""
from __future__ import annotations

import asyncio
from contextlib import suppress

from ..protocol.direct import ClientBase, Connect, Disconnect, Receive, Send, Sleep
from ..protocol.flow import AsyncRunner


class Client(AsyncRunner, ClientBase):
    """
    The direct connection (TA port) of the BL-NET with asyncio streams, see
    pyblnet.protocol.direct.ClientBase for its methods, which are awaitable
    here. The constructor doesn't connect, use create().
    """

    def __init__(self, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        super().__init__(address, port, reset, timeout)
        self._reader = None
        self._writer = None

    @classmethod
    async def create(cls, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        """Raises ConnectionError if the BL-NET mode is not supported"""
        client = cls(address, port, reset, timeout)
        await client.check_mode()
        return client

    async def _perform(self, operation):
        if isinstance(operation, Sleep):
            await asyncio.sleep(operation.seconds)
        elif isinstance(operation, Disconnect):
            await self._disconnect()
        else:
            return await asyncio.wait_for(self._perform_io(operation), self._timeout)

    async def _perform_io(self, operation):
        if isinstance(operation, Send):
            self._writer.write(operation.data)
            await self._writer.drain()
        elif isinstance(operation, Receive):
            return await self._reader.read(operation.max_size)
        elif isinstance(operation, Connect):
            try:
                self._reader, self._writer = await asyncio.open_connection(self.address, self.port)
            except OSError as err:
                raise ConnectionError("Could not connect to BLNET") from err
        else:
            raise TypeError(f"Unknown operation {operation}")

    async def _disconnect(self):
        writer, self._reader, self._writer = self._writer, None, None
        if writer is not None:
            writer.close()
            with suppress(OSError):
                await writer.wait_closed()

    async def close(self):
        """Close the connection if open and forget the read state"""
        await self._disconnect()
        self.protocol.forget()
