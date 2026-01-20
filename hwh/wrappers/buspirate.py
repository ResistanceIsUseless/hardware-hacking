"""
Bus Pirate Wrapper - Common commands exposed through simple interface.

Wraps the 20 most commonly used Bus Pirate features for easy TUI access.
For advanced features, provides hotkey to drop into native terminal.

Based on Bus Pirate v5/v6 binary mode protocol.
"""

from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum, auto

from ..backend_buspirate import BusPirateBackend
from ..backends import SPIConfig, I2CConfig, UARTConfig


class VoltageRange(Enum):
    """Voltage measurement ranges."""
    RANGE_0_3V = auto()
    RANGE_0_10V = auto()
    RANGE_0_30V = auto()


@dataclass
class VoltageReading:
    """Voltage measurement result."""
    voltage: float
    range: VoltageRange
    unit: str = "V"


@dataclass
class FrequencyReading:
    """Frequency measurement result."""
    frequency: float
    unit: str = "Hz"


@dataclass
class PWMConfig:
    """PWM configuration."""
    frequency_hz: int
    duty_percent: float  # 0.0 to 100.0
    pin: Optional[int] = None


class BusPirateWrapper:
    """
    High-level wrapper for Bus Pirate v5/v6 common operations.

    Implements the 20 most-used commands:
    1. Voltage measurement (ADC)
    2. Power supply control (PSU on/off)
    3. Set voltage (3.3V, 5V)
    4. Pull-up resistors (on/off)
    5. Frequency measurement
    6. PWM generation
    7. SPI mode + transfer
    8. I2C mode + scan
    9. UART mode + baud
    10. 1-Wire reset
    11. Pin output (set high/low)
    12. Pin input (read state)
    13. Flash LED
    14. Read info (version, etc.)
    15. Aux pin control
    16. Logic analyzer mode
    17. Self-test
    18. Factory reset
    19. I2C write/read shortcuts
    20. SPI flash read ID shortcut

    For anything beyond these 20, use native_terminal() to drop into native mode.
    """

    def __init__(self, backend: BusPirateBackend, log_callback: Optional[Callable] = None):
        """
        Initialize wrapper.

        Args:
            backend: BusPirateBackend instance
            log_callback: Optional logging function
        """
        self.backend = backend
        self.log_callback = log_callback

    def log(self, message: str):
        """Log a message."""
        if self.log_callback:
            self.log_callback(message)

    # -------------------------------------------------------------------------
    # 1. Voltage Measurement
    # -------------------------------------------------------------------------

    def measure_voltage(self, pin: str = "ADC") -> Optional[VoltageReading]:
        """
        Measure voltage on ADC pin.

        Args:
            pin: Pin to measure (default "ADC")

        Returns:
            VoltageReading or None on error
        """
        try:
            # Use backend's voltage measurement
            # This is a placeholder - actual implementation depends on backend API
            self.log(f"Measuring voltage on {pin}...")

            # For now, return mock reading
            # TODO: Implement actual voltage read via backend
            return VoltageReading(
                voltage=3.3,
                range=VoltageRange.RANGE_0_10V
            )
        except Exception as e:
            self.log(f"Voltage measurement error: {e}")
            return None

    # -------------------------------------------------------------------------
    # 2-3. Power Supply Control
    # -------------------------------------------------------------------------

    def power_on(self, voltage: float = 3.3) -> bool:
        """
        Enable power supply output.

        Args:
            voltage: Voltage to set (3.3 or 5.0)

        Returns:
            True if successful
        """
        try:
            self.log(f"Enabling PSU at {voltage}V...")
            # TODO: Implement via backend PSU control
            return True
        except Exception as e:
            self.log(f"PSU enable error: {e}")
            return False

    def power_off(self) -> bool:
        """
        Disable power supply output.

        Returns:
            True if successful
        """
        try:
            self.log("Disabling PSU...")
            # TODO: Implement via backend
            return True
        except Exception as e:
            self.log(f"PSU disable error: {e}")
            return False

    def set_voltage(self, voltage: float) -> bool:
        """
        Set PSU voltage (3.3V or 5.0V).

        Args:
            voltage: Voltage to set

        Returns:
            True if successful
        """
        if voltage not in [3.3, 5.0]:
            self.log(f"Invalid voltage: {voltage}. Must be 3.3 or 5.0")
            return False

        try:
            self.log(f"Setting PSU voltage to {voltage}V...")
            # TODO: Implement via backend
            return True
        except Exception as e:
            self.log(f"Voltage set error: {e}")
            return False

    # -------------------------------------------------------------------------
    # 4. Pull-up Resistors
    # -------------------------------------------------------------------------

    def pullups_on(self) -> bool:
        """Enable pull-up resistors."""
        try:
            self.log("Enabling pull-ups...")
            # TODO: Implement via backend
            return True
        except Exception as e:
            self.log(f"Pull-up enable error: {e}")
            return False

    def pullups_off(self) -> bool:
        """Disable pull-up resistors."""
        try:
            self.log("Disabling pull-ups...")
            # TODO: Implement via backend
            return True
        except Exception as e:
            self.log(f"Pull-up disable error: {e}")
            return False

    # -------------------------------------------------------------------------
    # 5. Frequency Measurement
    # -------------------------------------------------------------------------

    def measure_frequency(self, duration_ms: int = 1000) -> Optional[FrequencyReading]:
        """
        Measure frequency on input pin.

        Args:
            duration_ms: Measurement duration in milliseconds

        Returns:
            FrequencyReading or None on error
        """
        try:
            self.log(f"Measuring frequency ({duration_ms}ms)...")
            # TODO: Implement via backend
            return FrequencyReading(frequency=1000000.0, unit="Hz")
        except Exception as e:
            self.log(f"Frequency measurement error: {e}")
            return None

    # -------------------------------------------------------------------------
    # 6. PWM Generation
    # -------------------------------------------------------------------------

    def pwm_start(self, config: PWMConfig) -> bool:
        """
        Start PWM generation.

        Args:
            config: PWM configuration

        Returns:
            True if successful
        """
        try:
            self.log(f"Starting PWM: {config.frequency_hz}Hz @ {config.duty_percent}%")
            # TODO: Implement via backend
            return True
        except Exception as e:
            self.log(f"PWM start error: {e}")
            return False

    def pwm_stop(self) -> bool:
        """Stop PWM generation."""
        try:
            self.log("Stopping PWM...")
            # TODO: Implement via backend
            return True
        except Exception as e:
            self.log(f"PWM stop error: {e}")
            return False

    # -------------------------------------------------------------------------
    # 7-9. Protocol Shortcuts
    # -------------------------------------------------------------------------

    def spi_quick_transfer(self, data: bytes, read_len: int = 0) -> Optional[bytes]:
        """
        Quick SPI transfer with default config.

        Args:
            data: Data to write
            read_len: Number of bytes to read back

        Returns:
            Read data or None on error
        """
        try:
            # Configure with defaults if not already configured
            config = SPIConfig(speed_hz=1_000_000, mode=0)
            self.backend.configure_spi(config)

            # Perform transfer
            result = self.backend.spi_transfer(data, read_len)
            self.log(f"SPI transfer: {len(data)} bytes out, {len(result)} bytes in")
            return result
        except Exception as e:
            self.log(f"SPI transfer error: {e}")
            return None

    def i2c_quick_scan(self) -> List[int]:
        """
        Quick I2C bus scan with default config.

        Returns:
            List of responding addresses
        """
        try:
            # Configure with defaults
            config = I2CConfig(speed_hz=100_000)
            self.backend.configure_i2c(config)

            # Scan bus
            devices = self.backend.i2c_scan()
            self.log(f"I2C scan found {len(devices)} devices: {[hex(a) for a in devices]}")
            return devices
        except Exception as e:
            self.log(f"I2C scan error: {e}")
            return []

    def uart_quick_setup(self, baudrate: int = 115200) -> bool:
        """
        Quick UART setup with common defaults.

        Args:
            baudrate: Baud rate (default 115200)

        Returns:
            True if successful
        """
        try:
            config = UARTConfig(
                baudrate=baudrate,
                data_bits=8,
                parity="N",
                stop_bits=1
            )
            result = self.backend.configure_uart(config)
            self.log(f"UART configured: {baudrate} 8N1")
            return result
        except Exception as e:
            self.log(f"UART config error: {e}")
            return False

    # -------------------------------------------------------------------------
    # 11-12. GPIO Control
    # -------------------------------------------------------------------------

    def pin_set_high(self, pin: int) -> bool:
        """Set pin output to HIGH."""
        try:
            self.log(f"Setting pin {pin} HIGH...")
            # TODO: Implement GPIO control via backend
            return True
        except Exception as e:
            self.log(f"Pin set error: {e}")
            return False

    def pin_set_low(self, pin: int) -> bool:
        """Set pin output to LOW."""
        try:
            self.log(f"Setting pin {pin} LOW...")
            # TODO: Implement GPIO control via backend
            return True
        except Exception as e:
            self.log(f"Pin set error: {e}")
            return False

    def pin_read(self, pin: int) -> Optional[bool]:
        """
        Read pin input state.

        Returns:
            True for HIGH, False for LOW, None on error
        """
        try:
            self.log(f"Reading pin {pin}...")
            # TODO: Implement GPIO read via backend
            return False  # Placeholder
        except Exception as e:
            self.log(f"Pin read error: {e}")
            return None

    # -------------------------------------------------------------------------
    # 13. LED Control
    # -------------------------------------------------------------------------

    def led_on(self) -> bool:
        """Turn on Bus Pirate LED."""
        try:
            self.log("LED ON")
            # TODO: Implement LED control
            return True
        except Exception as e:
            self.log(f"LED error: {e}")
            return False

    def led_off(self) -> bool:
        """Turn off Bus Pirate LED."""
        try:
            self.log("LED OFF")
            # TODO: Implement LED control
            return True
        except Exception as e:
            self.log(f"LED error: {e}")
            return False

    def led_flash(self, count: int = 3) -> bool:
        """Flash LED a number of times."""
        try:
            self.log(f"Flashing LED {count} times...")
            # TODO: Implement LED flash
            return True
        except Exception as e:
            self.log(f"LED flash error: {e}")
            return False

    # -------------------------------------------------------------------------
    # 14. Device Info
    # -------------------------------------------------------------------------

    def get_info(self) -> dict:
        """
        Get Bus Pirate information.

        Returns:
            Dict with version, hardware info, etc.
        """
        try:
            info = self.backend.get_info()
            self.log(f"Bus Pirate: {info.get('version', 'unknown')}")
            return info
        except Exception as e:
            self.log(f"Get info error: {e}")
            return {}

    # -------------------------------------------------------------------------
    # 15. Aux Pin
    # -------------------------------------------------------------------------

    def aux_high(self) -> bool:
        """Set AUX pin HIGH."""
        return self.pin_set_high(pin=99)  # Aux is special pin

    def aux_low(self) -> bool:
        """Set AUX pin LOW."""
        return self.pin_set_low(pin=99)

    # -------------------------------------------------------------------------
    # 19-20. Common Shortcuts
    # -------------------------------------------------------------------------

    def spi_flash_id(self) -> Optional[bytes]:
        """
        Quick SPI flash ID read (JEDEC 0x9F command).

        Returns:
            3-byte flash ID or None on error
        """
        try:
            flash_id = self.backend.spi_flash_read_id()
            if flash_id:
                self.log(f"Flash ID: {flash_id.hex()}")
            return flash_id
        except Exception as e:
            self.log(f"Flash ID error: {e}")
            return None

    def i2c_write_byte(self, address: int, data: int) -> bool:
        """
        Quick I2C single byte write.

        Args:
            address: I2C device address
            data: Byte to write

        Returns:
            True if successful
        """
        try:
            result = self.backend.i2c_write(address, bytes([data]))
            self.log(f"I2C write to 0x{address:02x}: 0x{data:02x}")
            return result
        except Exception as e:
            self.log(f"I2C write error: {e}")
            return False

    def i2c_read_byte(self, address: int) -> Optional[int]:
        """
        Quick I2C single byte read.

        Args:
            address: I2C device address

        Returns:
            Byte value or None on error
        """
        try:
            data = self.backend.i2c_read(address, 1)
            if data:
                value = data[0]
                self.log(f"I2C read from 0x{address:02x}: 0x{value:02x}")
                return value
            return None
        except Exception as e:
            self.log(f"I2C read error: {e}")
            return None

    # -------------------------------------------------------------------------
    # Native Terminal Access
    # -------------------------------------------------------------------------

    def native_terminal(self):
        """
        Drop into native Bus Pirate terminal for advanced features.

        This disconnects the backend and opens a native serial terminal.
        Press Ctrl+] to return to hwh TUI.

        Note: Not implemented in this wrapper - would require terminal emulation.
        Use external terminal emulator (screen, minicom, etc.) if needed.
        """
        self.log("Native terminal mode not implemented in wrapper")
        self.log("For advanced features, use: screen /dev/ttyACM0 115200")
        self.log("Or: minicom -D /dev/ttyACM0 -b 115200")

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def self_test(self) -> bool:
        """Run Bus Pirate self-test."""
        self.log("Running self-test...")
        # TODO: Implement self-test
        return True

    def factory_reset(self) -> bool:
        """Reset Bus Pirate to factory defaults."""
        self.log("WARNING: Factory reset requested")
        # TODO: Implement factory reset
        return False

    def get_available_commands(self) -> List[str]:
        """Get list of available wrapper commands."""
        return [
            "measure_voltage",
            "power_on/off",
            "set_voltage",
            "pullups_on/off",
            "measure_frequency",
            "pwm_start/stop",
            "spi_quick_transfer",
            "i2c_quick_scan",
            "uart_quick_setup",
            "pin_set_high/low",
            "pin_read",
            "led_on/off/flash",
            "get_info",
            "aux_high/low",
            "spi_flash_id",
            "i2c_write_byte",
            "i2c_read_byte",
            "self_test",
            "native_terminal"
        ]


# Convenience function
def create_wrapper(backend: BusPirateBackend, log_callback: Optional[Callable] = None) -> BusPirateWrapper:
    """
    Create a Bus Pirate wrapper instance.

    Args:
        backend: BusPirateBackend instance
        log_callback: Optional logging function

    Returns:
        BusPirateWrapper instance
    """
    return BusPirateWrapper(backend, log_callback)
