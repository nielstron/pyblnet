#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .blnet_web import BLNETWeb, test_blnet
from .blnet_conn import BLNETDirect
from .blnet import BLNET

VERSION = (0, 7, 4)

__version__ = '.'.join([str(i) for i in VERSION])
__author__ = 'nielstron'
__author_email__ = 'n.muendler@web.de'
__copyright__ = 'Copyright (C) 2019 nielstron'
__license__ = "MIT"
__url__ = "https://github.com/nielstron/pyblnet"
