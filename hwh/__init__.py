"""
hwh - Unified Hardware Hacking Tool

A single interface for ST-Link, Bus Pirate, Tigard, Curious Bolt, and FaultyCat.
"""

__version__ = "0.1.0"

from .detect import detect, list_devices
from .backends import get_backend

__all__ = ["detect", "list_devices", "get_backend", "__version__"]
