"""
Run the flows of the sans-I/O protocol modules.

A flow is a generator that yields the I/O operations it needs, e.g. an HTTP
request or bytes to send, and gets their results sent back. It doesn't do
any I/O itself, so the same flow runs blocking (run_sync) and with asyncio
(run_async). The callers only implement how to perform an operation.
Exceptions raised while performing an operation are thrown into the flow,
which may handle them.

The client base classes in the protocol modules implement the API of the
clients once: their methods return self._run(flow). The blocking clients
mix in SyncRunner, so the methods return the result. The async clients mix
in AsyncRunner, so the same methods return an awaitable of the result.
"""


def run_sync(flow, perform):
    """Run flow, performing its operations with perform(operation)"""
    try:
        operation = next(flow)
        while True:
            try:
                result = perform(operation)
            except BaseException as err:
                operation = flow.throw(err)
            else:
                operation = flow.send(result)
    except StopIteration as done:
        return done.value


async def run_async(flow, perform):
    """Run flow, performing its operations with await perform(operation)"""
    try:
        operation = next(flow)
        while True:
            try:
                result = await perform(operation)
            except BaseException as err:
                operation = flow.throw(err)
            else:
                operation = flow.send(result)
    except StopIteration as done:
        return done.value


class SyncRunner:
    """Run flows blocking, with the operations performed by self._perform"""

    def _run(self, flow):
        return run_sync(flow, self._perform)


class AsyncRunner:
    """Run flows with asyncio, with the operations performed by await self._perform"""

    async def _run(self, flow):
        return await run_async(flow, self._perform)
