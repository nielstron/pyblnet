"""Blocking clients for the BL-NET, with requests and sockets"""
from .client import Client
from . import direct, web

__all__ = ["Client", "direct", "web"]
