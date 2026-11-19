"""
The protocols of the BL-NET without I/O, shared by the blocking clients in
pyblnet.sync and the async ones in pyblnet.aio. The flows are generators
that yield the I/O operations they need and get their results sent back,
see flow.py.
"""
