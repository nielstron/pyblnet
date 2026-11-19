#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings

try:
    from .sync.client import Client
    from .sync.web import blnet_test
except ImportError as e:
    warnings.warn(ImportWarning(e))

VERSION = (0, 12, 0)

