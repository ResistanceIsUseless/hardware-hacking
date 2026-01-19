"""
Bus Pirate 5/6 backend using BPIO2 FlatBuffers protocol.

Supports: SPI, I2C, UART, 1-Wire, PSU control
Reference: https://docs.buspirate.com/docs/binmode-reference/protocol-bpio2/
"""

import struct
from typing import Any, Optional

from .backends import (
    BusBackend, register_backend,
    SPIConfig, I2CConfig, UARTConfig
)
from .detect import DeviceInfo
from .bpio2_protocol import BPIO2Protocol


class BusPirateBackend(BusBackend):
    """
    Backend for Bus Pirate 5/6 using BPIO2 FlatBuffers interface.
    
    The Bus Pirate exposes two serial ports:
    - Port 0: Terminal/console
    - Port 1: BPIO2 binary interface
    
    We use the BPIO2 interface for programmatic control.
    """
    
    # BPIO2 protocol constants
    BPIO2_VERSION_MAJOR = 2
    
    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self._serial = None
        self._bpio2 = BPIO2Protocol()
        self._current_mode = None
        self._psu_enabled = False
        self._psu_voltage_mv = 3300
    
    def connect(self) -> bool:
        """Connect to Bus Pirate BPIO2 interface."""
        if not self.device.port:
            print(f"[BusPirate] No port specified for {self.device.name}")
            return False

        try:
            import serial
            from cobs import cobs
        except ImportError as e:
            print(f"[BusPirate] Missing dependency: {e}")
            print("  Install with: pip install pyserial cobs")
            return False

        try:
            # BPIO2 runs on the second serial port (interface 3, not 1)
            # Bus Pirate exposes:
            #   - Interface 1 (/dev/*buspirate1): Console/terminal
            #   - Interface 3 (/dev/*buspirate3): BPIO2 binary mode
            bpio2_port = self.device.port.replace('buspirate1', 'buspirate3')

            print(f"[BusPirate] Trying BPIO2 port: {bpio2_port}")

            self._serial = serial.Serial(
                bpio2_port,
                baudrate=115200,
                timeout=2  # Longer timeout for initial connection
            )
            self._connected = True

            # Verify connection with status request
            print(f"[BusPirate] Sending status request...")
            status = self._status_request()
            if status:
                mode = status.get('mode', 'unknown')
                print(f"[BusPirate] Connected: {mode} mode")
                self._current_mode = mode
                return True
            else:
                print(f"[BusPirate] No response from status request")
                self.disconnect()
                return False

        except Exception as e:
            print(f"[BusPirate] Connection failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def disconnect(self):
        """Disconnect from Bus Pirate."""
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self._connected = False
    
    def get_info(self) -> dict[str, Any]:
        """Get Bus Pirate status information."""
        if not self._connected:
            return {"error": "Not connected"}
        return self._status_request() or {"error": "Status request failed"}
    
    # --------------------------------------------------------------------------
    # BPIO2 Protocol Implementation
    # --------------------------------------------------------------------------
    
    def _receive_message(self) -> Optional[bytes]:
        """
        Receive COBS-encoded message from Bus Pirate.

        Returns:
            Decoded FlatBuffers data or None on timeout/error
        """
        # Read until 0x00 delimiter
        response = b''
        while True:
            byte = self._serial.read(1)
            if not byte:
                return None  # Timeout
            if byte == b'\x00':
                break
            response += byte

        # COBS decode
        try:
            return self._bpio2.decode_message(response)
        except Exception as e:
            print(f"[BusPirate] Decode error: {e}")
            return None
    
    def _status_request(self) -> Optional[dict]:
        """Send StatusRequest and parse StatusResponse."""
        if not self._connected:
            return None

        # Build status request
        request = self._bpio2.build_status_request()
        encoded = self._bpio2.encode_message(request)

        # Send and receive
        self._serial.write(encoded)
        self._serial.flush()

        # Read response
        response_data = self._receive_message()
        if not response_data:
            return None

        # Parse response
        response = self._bpio2.parse_response(response_data)
        if response and 'data' in response:
            return response['data']

        return None
    
    def _configure_mode(self, mode: str, mode_config: Optional[dict] = None, **kwargs) -> bool:
        """
        Send ConfigurationRequest to change mode.

        Args:
            mode: Mode name (SPI, I2C, UART, etc.)
            mode_config: Dict of mode-specific configuration
            **kwargs: Additional configuration (PSU, pullups, etc.)
        """
        if not self._connected:
            return False

        # Build configuration request
        request = self._bpio2.build_configuration_request(
            mode=mode,
            mode_config=mode_config,
            **kwargs
        )
        encoded = self._bpio2.encode_message(request)

        # Send and receive
        self._serial.write(encoded)
        self._serial.flush()

        # Read response
        response_data = self._receive_message()
        if not response_data:
            return False

        # Parse response
        response = self._bpio2.parse_response(response_data)
        if response and 'data' in response:
            data = response['data']
            if 'error' in data and data['error']:
                print(f"[BusPirate] Configuration error: {data['error']}")
                return False
            self._current_mode = mode
            return True

        return False
    
    def _data_request(self,
                      start: bool = False,
                      write_data: Optional[bytes] = None,
                      read_len: int = 0,
                      stop: bool = False) -> Optional[bytes]:
        """
        Send DataRequest for bus transactions.

        Args:
            start: Send start condition
            write_data: Data to write
            read_len: Number of bytes to read
            stop: Send stop condition
        """
        if not self._connected:
            return None

        # Build data request
        request = self._bpio2.build_data_request(
            write_data=write_data,
            read_len=read_len,
            start=start,
            stop=stop
        )
        encoded = self._bpio2.encode_message(request)

        # Send and receive
        self._serial.write(encoded)
        self._serial.flush()

        # Read response
        response_data = self._receive_message()
        if not response_data:
            return None

        # Parse response
        response = self._bpio2.parse_response(response_data)
        if response and 'data' in response:
            data = response['data']
            if 'error' in data and data['error']:
                print(f"[BusPirate] Data error: {data['error']}")
                return None
            return data.get('data_read', b'')

        return None
    
    # --------------------------------------------------------------------------
    # PSU Control (Bus Pirate specific)
    # --------------------------------------------------------------------------
    
    def set_psu(self, enabled: bool, voltage_mv: int = 3300, current_ma: int = 300) -> bool:
        """
        Control the onboard programmable power supply.

        Args:
            enabled: Enable/disable PSU
            voltage_mv: Output voltage in millivolts (1800-5000)
            current_ma: Current limit in milliamps (0 for unlimited)
        """
        if not self._connected:
            return False

        result = self._configure_mode(
            mode=None,  # Don't change mode
            psu_enable=enabled,
            psu_voltage_mv=voltage_mv if enabled else None,
            psu_current_ma=current_ma if enabled else None
        )

        if result:
            self._psu_enabled = enabled
            self._psu_voltage_mv = voltage_mv

        return result

    def set_pullups(self, enabled: bool) -> bool:
        """Enable/disable internal pull-up resistors."""
        if not self._connected:
            return False

        return self._configure_mode(
            mode=None,  # Don't change mode
            pullup_enable=enabled
        )
    
    # --------------------------------------------------------------------------
    # SPI Interface
    # --------------------------------------------------------------------------
    
    def configure_spi(self, config: SPIConfig) -> bool:
        """Configure SPI interface."""
        if not self._connected:
            return False

        # Map config to BPIO2 parameters
        clock_polarity = (config.mode >> 1) & 1  # CPOL
        clock_phase = config.mode & 1            # CPHA

        mode_config = {
            'speed': config.speed_hz,
            'clock_polarity': bool(clock_polarity),
            'clock_phase': bool(clock_phase),
            'chip_select_idle': config.cs_active_low
        }

        return self._configure_mode("SPI", mode_config=mode_config)
    
    def spi_transfer(self, write_data: bytes, read_len: int = 0) -> bytes:
        """Perform SPI transfer."""
        if not self._connected or self._current_mode != "SPI":
            return b''
        
        result = self._data_request(
            start=True,
            write_data=write_data,
            read_len=read_len,
            stop=True
        )
        return result or b''
    
    # --------------------------------------------------------------------------
    # I2C Interface
    # --------------------------------------------------------------------------
    
    def configure_i2c(self, config: I2CConfig) -> bool:
        """Configure I2C interface."""
        if not self._connected:
            return False

        mode_config = {
            'speed': config.speed_hz
        }

        return self._configure_mode("I2C", mode_config=mode_config)
    
    def i2c_write(self, address: int, data: bytes) -> bool:
        """Write data to I2C device."""
        if not self._connected or self._current_mode != "I2C":
            return False
        
        # I2C address is 7-bit, shifted left with W bit (0)
        addr_byte = (address << 1) & 0xFE
        
        result = self._data_request(
            start=True,
            write_data=bytes([addr_byte]) + data,
            stop=True
        )
        return result is not None
    
    def i2c_read(self, address: int, length: int) -> bytes:
        """Read data from I2C device."""
        if not self._connected or self._current_mode != "I2C":
            return b''
        
        # I2C address with R bit (1)
        addr_byte = ((address << 1) | 1) & 0xFF
        
        result = self._data_request(
            start=True,
            write_data=bytes([addr_byte]),
            read_len=length,
            stop=True
        )
        return result or b''
    
    def i2c_write_read(self, address: int, write_data: bytes, read_len: int) -> bytes:
        """Write then read from I2C device (repeated start)."""
        if not self._connected or self._current_mode != "I2C":
            return b''
        
        # Full transaction with repeated start is handled by BPIO2
        addr_byte = (address << 1) & 0xFE
        
        result = self._data_request(
            start=True,
            write_data=bytes([addr_byte]) + write_data,
            read_len=read_len,
            stop=True
        )
        return result or b''
    
    def i2c_scan(self, start_addr: int = 0x08, end_addr: int = 0x77) -> list[int]:
        """Scan I2C bus for devices."""
        if not self._connected or self._current_mode != "I2C":
            return []
        
        found = []
        for addr in range(start_addr, end_addr + 1):
            # Try to read 0 bytes - ACK means device present
            addr_byte = ((addr << 1) | 1) & 0xFF
            result = self._data_request(
                start=True,
                write_data=bytes([addr_byte]),
                read_len=0,
                stop=True
            )
            # TODO: Check for ACK in response
            # For now, stub
        
        print(f"[BusPirate] STUB: i2c_scan - needs proper ACK detection")
        return found
    
    # --------------------------------------------------------------------------
    # UART Interface
    # --------------------------------------------------------------------------
    
    def configure_uart(self, config: UARTConfig) -> bool:
        """Configure UART interface."""
        if not self._connected:
            return False

        parity_map = {"N": False, "E": True, "O": True}  # Simplified

        mode_config = {
            'speed': config.baudrate,
            'data_bits': config.data_bits,
            'parity': parity_map.get(config.parity, False),
            'stop_bits': config.stop_bits
        }

        return self._configure_mode("UART", mode_config=mode_config)
    
    def uart_write(self, data: bytes):
        """Write data to UART."""
        if not self._connected or self._current_mode != "UART":
            return
        
        self._data_request(write_data=data)
    
    def uart_read(self, length: int, timeout_ms: int = 1000) -> bytes:
        """Read data from UART."""
        if not self._connected or self._current_mode != "UART":
            return b''

        result = self._data_request(read_len=length)
        return result or b''

    # --------------------------------------------------------------------------
    # SPI Flash Operations (Required by BusBackend)
    # --------------------------------------------------------------------------

    def spi_flash_read_id(self) -> bytes:
        """Read SPI flash JEDEC ID (0x9F command)."""
        if not self._connected or self._current_mode != "SPI":
            return b''
        return self.spi_transfer(b'\x9f', read_len=3)

    def spi_flash_read(self, address: int, length: int) -> bytes:
        """Read from SPI flash memory."""
        if not self._connected or self._current_mode != "SPI":
            return b''

        # Standard SPI flash read command: 0x03 + 24-bit address
        cmd = bytes([
            0x03,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF
        ])
        return self.spi_transfer(cmd, read_len=length)


# Register this backend for buspirate device type
register_backend("buspirate", BusPirateBackend)
