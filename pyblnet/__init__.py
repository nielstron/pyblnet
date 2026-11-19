#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings

try:
    from .sync.client import Client
except ImportError as e:
    warnings.warn(ImportWarning(e))

VERSION = (0, 12, 0)

