"""
Tigard backend using pyftdi for SPI/I2C/UART and OpenOCD for JTAG/SWD.

Reference: https://github.com/tigard-tools/tigard
"""

from typing import Any, Optional

from .backends import (
    BusBackend, DebugBackend, register_backend,
    SPIConfig, I2CConfig, UARTConfig
)
from .detect import DeviceInfo


class TigardBackend(BusBackend):
    """
    Backend for Tigard (FT2232H-based) hardware tool.
    
    Uses pyftdi for bus protocols (SPI, I2C, UART).
    JTAG/SWD requires OpenOCD - see TigardDebugBackend.
    
    Tigard has two channels:
    - Channel A: UART
    - Channel B: SPI/I2C/JTAG/SWD (directly controlled via MPSSE)
    """
    
    # FTDI device URL format for pyftdi
    FTDI_URL_TEMPLATE = "ftdi://ftdi:2232h:{serial}/2"  # Channel B
    
    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self._spi = None
        self._i2c = None
        self._uart = None
        self._ftdi_url = None
        self._current_protocol = None
    
    def connect(self) -> bool:
        """Connect to Tigard via pyftdi."""
        try:
            from pyftdi.ftdi import Ftdi
        except ImportError:
            print("[Tigard] pyftdi not installed")
            print("  Install with: pip install pyftdi")
            return False
        
        try:
            # Build FTDI URL
            if self.device.serial:
                self._ftdi_url = f"ftdi://ftdi:2232h:{self.device.serial}/2"
            else:
                # Use first available FT2232H
                self._ftdi_url = "ftdi://ftdi:2232h/2"
            
            # Verify device is accessible
            Ftdi.show_devices()
            self._connected = True
            print(f"[Tigard] Ready at {self._ftdi_url}")
            return True
            
        except Exception as e:
            print(f"[Tigard] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Tigard."""
        if self._spi:
            try:
                self._spi.close()
            except Exception:
                pass
            self._spi = None
        
        if self._i2c:
            try:
                self._i2c.close()
            except Exception:
                pass
            self._i2c = None
        
        self._connected = False
        self._current_protocol = None
    
    def get_info(self) -> dict[str, Any]:
        """Get Tigard information."""
        return {
            "name": "Tigard",
            "ftdi_url": self._ftdi_url,
            "current_protocol": self._current_protocol,
            "capabilities": ["spi", "i2c", "uart", "jtag", "swd"],
        }
    
    # --------------------------------------------------------------------------
    # SPI Interface
    # --------------------------------------------------------------------------
    
    def configure_spi(self, config: SPIConfig) -> bool:
        """Configure SPI interface."""
        if not self._connected:
            return False
        
        # Close any existing protocol controller
        self._close_current_protocol()
        
        try:
            from pyftdi.spi import SpiController
            
            ctrl = SpiController()
            ctrl.configure(self._ftdi_url)
            
            # Get SPI port with configuration
            # Mode maps to CPOL/CPHA
            self._spi = ctrl.get_port(
                cs=0,
                freq=config.speed_hz,
                mode=config.mode
            )
            
            self._current_protocol = "SPI"
            print(f"[Tigard] SPI configured: {config.speed_hz}Hz, mode {config.mode}")
            return True
            
        except Exception as e:
            print(f"[Tigard] SPI configuration failed: {e}")
            return False
    
    def spi_transfer(self, write_data: bytes, read_len: int = 0) -> bytes:
        """Perform SPI transfer."""
        if not self._spi:
            return b''
        
        try:
            if read_len > 0 and write_data:
                # Write then read
                return bytes(self._spi.exchange(write_data, read_len))
            elif read_len > 0:
                # Read only
                return bytes(self._spi.read(read_len))
            elif write_data:
                # Write only
                self._spi.write(write_data)
                return b''
            return b''
            
        except Exception as e:
            print(f"[Tigard] SPI transfer failed: {e}")
            return b''
    
    def spi_flash_read_id(self) -> bytes:
        """Read SPI flash JEDEC ID (command 0x9F)."""
        return self.spi_transfer(b'\x9f', read_len=3)
    
    def spi_flash_read(self, address: int, length: int) -> bytes:
        """Read from SPI flash."""
        # Standard read command: 0x03 + 24-bit address
        cmd = bytes([0x03, (address >> 16) & 0xFF, (address >> 8) & 0xFF, address & 0xFF])
        return self.spi_transfer(cmd, read_len=length)
    
    # --------------------------------------------------------------------------
    # I2C Interface
    # --------------------------------------------------------------------------
    
    def configure_i2c(self, config: I2CConfig) -> bool:
        """Configure I2C interface."""
        if not self._connected:
            return False
        
        self._close_current_protocol()
        
        try:
            from pyftdi.i2c import I2cController
            
            ctrl = I2cController()
            ctrl.configure(self._ftdi_url, frequency=config.speed_hz)
            self._i2c = ctrl
            
            self._current_protocol = "I2C"
            print(f"[Tigard] I2C configured: {config.speed_hz}Hz")
            return True
            
        except Exception as e:
            print(f"[Tigard] I2C configuration failed: {e}")
            return False
    
    def i2c_write(self, address: int, data: bytes) -> bool:
        """Write data to I2C device."""
        if not self._i2c:
            return False
        
        try:
            port = self._i2c.get_port(address)
            port.write(data)
            return True
        except Exception as e:
            print(f"[Tigard] I2C write failed: {e}")
            return False
    
    def i2c_read(self, address: int, length: int) -> bytes:
        """Read data from I2C device."""
        if not self._i2c:
            return b''
        
        try:
            port = self._i2c.get_port(address)
            return bytes(port.read(length))
        except Exception as e:
            print(f"[Tigard] I2C read failed: {e}")
            return b''
    
    def i2c_write_read(self, address: int, write_data: bytes, read_len: int) -> bytes:
        """Write then read from I2C device (repeated start)."""
        if not self._i2c:
            return b''
        
        try:
            port = self._i2c.get_port(address)
            return bytes(port.exchange(write_data, read_len))
        except Exception as e:
            print(f"[Tigard] I2C exchange failed: {e}")
            return b''
    
    def i2c_scan(self) -> list[int]:
        """Scan I2C bus for devices."""
        if not self._i2c:
            return []
        
        found = []
        for addr in range(0x08, 0x78):
            try:
                port = self._i2c.get_port(addr)
                port.read(0)  # Try to read - will raise if no ACK
                found.append(addr)
            except Exception:
                pass
        
        return found
    
    # --------------------------------------------------------------------------
    # UART Interface
    # --------------------------------------------------------------------------
    
    def configure_uart(self, config: UARTConfig) -> bool:
        """Configure UART interface (uses Channel A)."""
        if not self._connected:
            return False
        
        try:
            import serial
            
            # UART is on the first serial port associated with the FT2232H
            # This is typically the device.port
            if self.device.port:
                self._uart = serial.Serial(
                    self.device.port,
                    baudrate=config.baudrate,
                    bytesize=config.data_bits,
                    parity=config.parity,
                    stopbits=config.stop_bits,
                    timeout=1
                )
                self._current_protocol = "UART"
                print(f"[Tigard] UART configured: {config.baudrate} baud")
                return True
            else:
                print("[Tigard] No serial port available for UART")
                return False
                
        except Exception as e:
            print(f"[Tigard] UART configuration failed: {e}")
            return False
    
    def uart_write(self, data: bytes):
        """Write data to UART."""
        if self._uart:
            self._uart.write(data)
    
    def uart_read(self, length: int, timeout_ms: int = 1000) -> bytes:
        """Read data from UART."""
        if not self._uart:
            return b''
        
        self._uart.timeout = timeout_ms / 1000.0
        return self._uart.read(length)
    
    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    
    def _close_current_protocol(self):
        """Close current protocol controller before switching."""
        if self._spi:
            try:
                self._spi._controller.close()
            except Exception:
                pass
            self._spi = None
        
        if self._i2c:
            try:
                self._i2c.close()
            except Exception:
                pass
            self._i2c = None


class TigardDebugBackend(DebugBackend):
    """
    Tigard debug backend using OpenOCD for JTAG/SWD.
    
    This wraps OpenOCD subprocess calls since pyftdi doesn't support
    debug protocols directly.
    """
    
    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self._openocd_proc = None
    
    def connect(self) -> bool:
        """Start OpenOCD server for Tigard."""
        # TODO: Implement OpenOCD subprocess management
        print("[Tigard] Debug backend requires OpenOCD")
        print("  Use: openocd -f tigard-jtag.cfg (or tigard-swd.cfg)")
        return False
    
    def disconnect(self):
        """Stop OpenOCD server."""
        if self._openocd_proc:
            self._openocd_proc.terminate()
            self._openocd_proc = None
        self._connected = False
    
    def get_info(self) -> dict[str, Any]:
        return {"error": "Not implemented - use OpenOCD directly"}
    
    # Stub implementations for DebugBackend interface
    def connect_target(self, target: str = "auto") -> bool:
        return False
    
    def halt(self) -> bool:
        return False
    
    def resume(self) -> bool:
        return False
    
    def reset(self, halt: bool = False) -> bool:
        return False
    
    def read_memory(self, address: int, size: int) -> bytes:
        return b''
    
    def write_memory(self, address: int, data: bytes) -> bool:
        return False
    
    def set_breakpoint(self, address: int) -> int:
        return 0
    
    def remove_breakpoint(self, bp_id: int) -> bool:
        return False
    
    def read_registers(self) -> dict[str, int]:
        return {}


# Register backends
register_backend("tigard", TigardBackend)
