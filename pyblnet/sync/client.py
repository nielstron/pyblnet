#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on 13.08.2018

General high-level BLNET interface, blocking. The API is in
pyblnet.protocol.client.ClientBase.

@author: Nielstron
"""
from ..protocol.client import ClientBase, direct_host, web_address
from ..protocol.flow import SyncRunner
from . import direct, web


class Client(SyncRunner, ClientBase):
    """
    Read and control the BL-NET via the web interface and/or the direct
    connection, see pyblnet.protocol.client.ClientBase for its methods.
    Attributes:
    address      ip address of the BLNET
    web_port     port of the HTTP interface
    password     password for authenticating on the HTTP interface
    ta_port      port of the PC-BLNET interface
    timeout      timeout for requests
    max_retries  maximum number of connection retries before aborting
    use_web      boolean about whether to make use of the HTTP interface
    use_ta       boolean about whether to make use of the (buggy) PC-BLNET interface
    """

    def __init__(
        self,
        address,
        web_port=80,
        password=None,
        ta_port=40000,
        timeout=5,
        max_retries=5,
        use_web=True,
        use_ta=False,
    ):
        """
        If a connection (Web or TA/Direct) should not be used,
        set the corresponding use_* to False
        """
        assert isinstance(address, str)
        assert web_port is None or isinstance(web_port, int)
        assert ta_port is None or isinstance(ta_port, int)
        assert timeout is None or isinstance(timeout, int)
        self.address = address
        self.timeout = timeout
        super().__init__(
            web.Client(web_address(address, web_port), password, timeout) if use_web else None,
            direct.Client(direct_host(address), ta_port, timeout=timeout) if use_ta else None,
            max_retries,
        )
