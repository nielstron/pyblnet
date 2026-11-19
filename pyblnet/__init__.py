#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Read and control a UVR1611 via a BL-NET"""

from .sync.client import Client

__all__ = ["Client"]

# the version of the package, pyproject.toml reads it from here
__version__ = "1.0.0"
VERSION = tuple(int(part) for part in __version__.split("."))
