"""
hwh - Hardware Hacking Toolkit

A unified interface for hardware security tools with multi-device coordination,
intelligent automation, and profile-guided attacks.

Supports: ST-Link, Bus Pirate, Tigard, Curious Bolt, FaultyCat

Usage:
    # Command-line interface
    hwh detect              # Detect connected devices
    hwh tui                 # Terminal UI (interactive)
    hwh shell               # Interactive Python shell

    # Python API
    from hwh import detect, get_backend
    devices = detect()
    backend = get_backend(devices['buspirate'])
"""

__version__ = "0.1.0"

from .detect import detect, list_devices
from .backends import get_backend

__all__ = ["detect", "list_devices", "get_backend", "__version__"]
