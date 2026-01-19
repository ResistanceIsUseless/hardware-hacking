"""
Backend abstraction layer for hardware tools.

Each backend implements a common interface for its device type.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum, auto

from .detect import DeviceInfo


# --------------------------------------------------------------------------
# Common Types
# --------------------------------------------------------------------------

class BusProtocol(Enum):
    """Supported bus protocols."""
    SPI = auto()
    I2C = auto()
    UART = auto()
    JTAG = auto()
    SWD = auto()
    ONEWIRE = auto()


class TriggerEdge(Enum):
    """Trigger edge types for glitching/capture."""
    RISING = auto()
    FALLING = auto()
    EITHER = auto()


@dataclass
class SPIConfig:
    """SPI bus configuration."""
    speed_hz: int = 1_000_000
    mode: int = 0  # 0-3 (CPOL/CPHA combinations)
    bits_per_word: int = 8
    cs_active_low: bool = True


@dataclass
class I2CConfig:
    """I2C bus configuration."""
    speed_hz: int = 400_000
    address_bits: int = 7


@dataclass
class UARTConfig:
    """UART configuration."""
    baudrate: int = 115200
    data_bits: int = 8
    parity: str = "N"  # N, E, O
    stop_bits: int = 1


@dataclass  
class GlitchConfig:
    """Voltage glitch configuration."""
    width_ns: int = 100  # Glitch pulse width in nanoseconds
    offset_ns: int = 0   # Delay after trigger before glitch
    repeat: int = 1      # Number of glitch pulses
    trigger_channel: Optional[int] = None  # External trigger channel
    trigger_edge: TriggerEdge = TriggerEdge.FALLING


# --------------------------------------------------------------------------
# Backend Base Classes
# --------------------------------------------------------------------------

class Backend(ABC):
    """Base class for all hardware backends."""
    
    def __init__(self, device: DeviceInfo):
        self.device = device
        self._connected = False
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to device. Returns True on success."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection to device."""
        pass
    
    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        """Get device information/status."""
        pass
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class BusBackend(Backend):
    """Backend supporting bus protocols (SPI, I2C, UART)."""
    
    @abstractmethod
    def configure_spi(self, config: SPIConfig) -> bool:
        """Configure SPI interface."""
        pass
    
    @abstractmethod
    def spi_transfer(self, write_data: bytes, read_len: int = 0) -> bytes:
        """Perform SPI transfer. Returns read data."""
        pass
    
    @abstractmethod
    def configure_i2c(self, config: I2CConfig) -> bool:
        """Configure I2C interface."""
        pass
    
    @abstractmethod
    def i2c_write(self, address: int, data: bytes) -> bool:
        """Write data to I2C device."""
        pass
    
    @abstractmethod
    def i2c_read(self, address: int, length: int) -> bytes:
        """Read data from I2C device."""
        pass
    
    @abstractmethod
    def i2c_write_read(self, address: int, write_data: bytes, read_len: int) -> bytes:
        """Write then read from I2C device (repeated start)."""
        pass
    
    @abstractmethod
    def configure_uart(self, config: UARTConfig) -> bool:
        """Configure UART interface."""
        pass
    
    @abstractmethod
    def uart_write(self, data: bytes):
        """Write data to UART."""
        pass
    
    @abstractmethod
    def uart_read(self, length: int, timeout_ms: int = 1000) -> bytes:
        """Read data from UART."""
        pass

    @abstractmethod
    def spi_flash_read_id(self) -> bytes:
        """
        Read SPI flash JEDEC ID (0x9F command).

        Returns 3-byte manufacturer/device ID or empty bytes on error.
        """
        pass

    @abstractmethod
    def spi_flash_read(self, address: int, length: int) -> bytes:
        """
        Read data from SPI flash memory.

        Args:
            address: Start address in flash
            length: Number of bytes to read

        Returns:
            Data read from flash or empty bytes on error
        """
        pass

    @abstractmethod
    def i2c_scan(self, start_addr: int = 0x08, end_addr: int = 0x77) -> list[int]:
        """
        Scan I2C bus for devices.

        Args:
            start_addr: Starting address (default 0x08)
            end_addr: Ending address (default 0x77)

        Returns:
            List of addresses that responded with ACK
        """
        pass


class DebugBackend(Backend):
    """Backend supporting debug protocols (SWD, JTAG)."""
    
    @abstractmethod
    def connect_target(self, target: str = "auto") -> bool:
        """Connect to debug target. Target can be chip name or 'auto'."""
        pass
    
    @abstractmethod
    def halt(self) -> bool:
        """Halt the target CPU."""
        pass
    
    @abstractmethod
    def resume(self) -> bool:
        """Resume target execution."""
        pass
    
    @abstractmethod
    def reset(self, halt: bool = False) -> bool:
        """Reset target. If halt=True, halt after reset."""
        pass
    
    @abstractmethod
    def read_memory(self, address: int, size: int) -> bytes:
        """Read memory from target."""
        pass
    
    @abstractmethod
    def write_memory(self, address: int, data: bytes) -> bool:
        """Write memory to target."""
        pass
    
    @abstractmethod
    def set_breakpoint(self, address: int) -> int:
        """Set hardware breakpoint. Returns breakpoint ID."""
        pass
    
    @abstractmethod
    def remove_breakpoint(self, bp_id: int) -> bool:
        """Remove breakpoint by ID."""
        pass
    
    @abstractmethod
    def read_registers(self) -> dict[str, int]:
        """Read all CPU registers."""
        pass

    @abstractmethod
    def dump_firmware(self, start_address: int, size: int, chunk_size: int = 4096) -> bytes:
        """
        Dump firmware from target memory.

        Args:
            start_address: Starting address to read from
            size: Total number of bytes to read
            chunk_size: Bytes per read operation (for progress tracking)

        Returns:
            Firmware data or empty bytes on error
        """
        pass


class GlitchBackend(Backend):
    """Backend supporting fault injection."""
    
    @abstractmethod
    def configure_glitch(self, config: GlitchConfig) -> bool:
        """Configure glitch parameters."""
        pass
    
    @abstractmethod
    def arm(self) -> bool:
        """Arm the glitcher to wait for trigger."""
        pass
    
    @abstractmethod
    def trigger(self) -> bool:
        """Manually trigger a glitch."""
        pass
    
    @abstractmethod
    def disarm(self) -> bool:
        """Disarm the glitcher."""
        pass

    def run_glitch_sweep(self,
                         width_range: tuple[int, int],
                         width_step: int,
                         offset_range: tuple[int, int],
                         offset_step: int,
                         attempts_per_setting: int = 10,
                         callback=None) -> list[dict]:
        """
        Run a parameter sweep for glitch attacks.

        Args:
            width_range: (min, max) glitch width in nanoseconds
            width_step: Step size for width in nanoseconds
            offset_range: (min, max) offset after trigger in nanoseconds
            offset_step: Step size for offset in nanoseconds
            attempts_per_setting: Number of glitches at each parameter combination
            callback: Optional function called after each glitch

        Returns:
            List of result dictionaries with parameters and outcomes

        Note: This is a concrete method with default implementation.
              Backends can override for device-specific optimizations.
        """
        results = []

        for width in range(width_range[0], width_range[1] + 1, width_step):
            for offset in range(offset_range[0], offset_range[1] + 1, offset_step):
                config = GlitchConfig(width_ns=width, offset_ns=offset)
                self.configure_glitch(config)

                for attempt in range(attempts_per_setting):
                    self.trigger()

                    result = {
                        "width_ns": width,
                        "offset_ns": offset,
                        "attempt": attempt,
                    }

                    if callback:
                        callback_result = callback(config, attempt)
                        result["callback_result"] = callback_result

                    results.append(result)

        return results


# --------------------------------------------------------------------------
# Backend Registry
# --------------------------------------------------------------------------

_BACKEND_REGISTRY: dict[str, type[Backend]] = {}


def register_backend(device_type: str, backend_class: type[Backend]):
    """Register a backend class for a device type."""
    _BACKEND_REGISTRY[device_type] = backend_class


def get_backend(device: DeviceInfo) -> Optional[Backend]:
    """
    Get the appropriate backend instance for a device.
    
    Args:
        device: DeviceInfo from detection.
        
    Returns:
        Backend instance or None if no backend available.
    """
    backend_class = _BACKEND_REGISTRY.get(device.device_type)
    
    if backend_class is None:
        return None
    
    return backend_class(device)


def list_backends() -> dict[str, type[Backend]]:
    """List all registered backends."""
    return _BACKEND_REGISTRY.copy()


# --------------------------------------------------------------------------
# Import concrete backends to register them
# --------------------------------------------------------------------------

# These imports trigger registration via decorators or explicit calls
from . import backend_buspirate
from . import backend_bolt
from . import backend_stlink
from . import backend_tigard
from . import backend_blackmagic
