"""The direct connection (TA port) of the BL-NET, with asyncio streams"""
from __future__ import annotations

import asyncio
from contextlib import suppress

from ..protocol.direct import (
    INVALID_REPLY_ERRORS,
    MAX_RETRYS,
    Connect,
    DirectProtocol,
    Disconnect,
    Receive,
    Send,
    Sleep,
)
from ..protocol.flow import run_async


class DirectClient:
    """The direct connection (TA port) of the BL-NET, see pyblnet.sync.DirectClient"""

    def __init__(self, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        """Doesn't connect, use create() for that"""
        assert isinstance(address, str)
        assert isinstance(port, int)
        assert isinstance(reset, bool)
        self.address = address
        self.port = port
        self.reset = reset
        self._timeout = timeout or None
        self._reader = None
        self._writer = None
        self.protocol = DirectProtocol(reset)

    @classmethod
    async def create(cls, address, port: int = 40000, reset: bool = False, timeout: float = 60):
        """Raises ConnectionError if the BL-NET mode is not supported"""
        direct = cls(address, port, reset, timeout)
        await direct._run(direct.protocol.check_mode())
        return direct

    async def _run(self, flow):
        """
        Run a flow of the protocol. If it fails, close the connection and
        forget the read state, so that the next call starts afresh.
        Malformed replies are raised as ConnectionError.
        """
        try:
            return await run_async(flow, self._perform)
        except INVALID_REPLY_ERRORS as ex:
            await self.close()
            raise ConnectionError(f"Invalid reply from BL-Net: {ex}") from ex
        except BaseException:
            await self.close()
            raise

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
            if self._writer is None:
                try:
                    self._reader, self._writer = await asyncio.open_connection(
                        self.address, self.port
                    )
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

    async def get_count(self):
        return await self._run(self.protocol.get_count())

    async def get_data(self, max_count=None):
        """The datasets logged in the bootloader memory, up to max_count"""
        return await self._run(self.protocol.get_data(max_count))

    async def get_latest(self, max_retries=MAX_RETRYS):
        return await self._run(self.protocol.get_latest(max_retries))
