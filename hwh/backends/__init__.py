"""
Backend implementations for hardware devices.
"""

from .base import (
    Backend,
    BusBackend,
    DebugBackend,
    GlitchBackend,
    get_backend,
    register_backend,
    SPIConfig,
    I2CConfig,
    UARTConfig,
    GlitchConfig,
    TriggerEdge,
)

__all__ = [
    "Backend",
    "BusBackend",
    "DebugBackend",
    "GlitchBackend",
    "get_backend",
    "register_backend",
    "SPIConfig",
    "I2CConfig",
    "UARTConfig",
    "GlitchConfig",
    "TriggerEdge",
]
