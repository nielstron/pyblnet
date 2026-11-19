"""Blocking clients for the BL-NET, with requests and sockets"""
from .client import Client
from . import direct, web
from .web import blnet_test

__all__ = ["Client", "blnet_test", "direct", "web"]
