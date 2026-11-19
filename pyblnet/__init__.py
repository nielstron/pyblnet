#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings

try:
    from .sync.client import Client
except ImportError as e:
    warnings.warn(ImportWarning(e))

VERSION = (1, 0, 0)

