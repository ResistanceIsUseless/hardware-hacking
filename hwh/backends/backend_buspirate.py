"""
Bus Pirate 5/6 backend using official BPIO2 FlatBuffers protocol.

This backend wraps the official pybpio library from DangerousPrototypes.

Supports: SPI, I2C, UART, 1-Wire, PSU control
Reference: https://docs.buspirate.com/docs/binmode-reference/protocol-bpio2/
"""

from typing import Any, Optional

from .base import (
    BusBackend, register_backend,
    SPIConfig, I2CConfig, UARTConfig
)
from ..detect import DeviceInfo

# Import official BPIO2 library
from ..pybpio.bpio_client import BPIOClient
from ..pybpio.bpio_spi import BPIOSPI
from ..pybpio.bpio_i2c import BPIOI2C
from ..pybpio.bpio_uart import BPIOUART


class BusPirateBackend(BusBackend):
    """
    Backend for Bus Pirate 5/6 using official BPIO2 FlatBuffers interface.

    The Bus Pirate exposes two serial ports:
    - Port 0 (buspirate1): Terminal/console
    - Port 1 (buspirate3): BPIO2 binary interface

    We use the BPIO2 interface for programmatic control.
    """

    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self._client = None
        self._spi = None
        self._i2c = None
        self._uart = None
        self._current_mode = None

    def _enter_binary_mode(self, console_port: str) -> bool:
        """
        Enter BPIO2 binary mode via the console port.

        Args:
            console_port: Path to the console port (buspirate1)

        Returns:
            True if binary mode was entered successfully
        """
        import serial
        import time

        try:
            print(f"[BusPirate] Entering binary mode via console: {console_port}")

            # Open console port at 115200 baud
            console = serial.Serial(console_port, 115200, timeout=2)
            time.sleep(0.1)

            # Clear any existing data
            console.reset_input_buffer()
            console.reset_output_buffer()

            # Send binmode command
            console.write(b'binmode\r\n')
            time.sleep(0.5)

            # Read response (should show menu)
            response = b''
            if console.in_waiting > 0:
                response = console.read(console.in_waiting)
                print(f"[BusPirate] Menu response: {response.decode('utf-8', errors='ignore')[:200]}")

            # Select BBIO2 (option 2)
            print(f"[BusPirate] Selecting BBIO2 binary mode...")
            console.write(b'2\r\n')
            time.sleep(0.5)

            # Read confirmation
            if console.in_waiting > 0:
                response = console.read(console.in_waiting)
                print(f"[BusPirate] Mode change response: {response.decode('utf-8', errors='ignore')[:200]}")

            console.close()
            print(f"[BusPirate] Binary mode command sent, waiting for mode switch...")
            time.sleep(1)  # Give it time to switch modes

            return True

        except Exception as e:
            print(f"[BusPirate] Failed to enter binary mode: {e}")
            return False

    def connect(self) -> bool:
        """Connect to Bus Pirate BPIO2 interface."""
        if not self.device.port:
            print(f"[BusPirate] No port specified for {self.device.name}")
            return False

        try:
            # BPIO2 runs on the second serial port (interface 3, not 1)
            # Bus Pirate exposes:
            #   - Interface 1 (/dev/*buspirate1): Console/terminal
            #   - Interface 3 (/dev/*buspirate3): BPIO2 binary mode
            console_port = self.device.port  # buspirate1
            bpio2_port = self.device.port.replace('buspirate1', 'buspirate3')

            # Also handle cu.usbmodem format on macOS
            if 'cu.usbmodem' in bpio2_port and 'buspirate1' in bpio2_port:
                bpio2_port = bpio2_port.replace('buspirate1', 'buspirate3')

            # Try 1: Attempt to connect to BPIO2 port (might already be in binary mode)
            print(f"[BusPirate] Attempting direct connection to BPIO2 port: {bpio2_port}")
            try:
                self._client = BPIOClient(
                    port=bpio2_port,
                    baudrate=3000000,
                    timeout=1,  # Short timeout for first attempt
                    debug=False
                )
                status = self._client.status_request()
                if status:
                    # Success! Already in binary mode
                    self._connected = True
                    mode = status.get('mode_current', 'unknown')
                    fw_ver = f"{status['version_firmware_major']}.{status['version_firmware_minor']}"
                    hw_ver = f"{status['version_hardware_major']} REV{status['version_hardware_minor']}"
                    print(f"[BusPirate] Connected successfully (already in binary mode)!")
                    print(f"[BusPirate] Firmware: v{fw_ver}")
                    print(f"[BusPirate] Hardware: v{hw_ver}")
                    print(f"[BusPirate] Current mode: {mode}")
                    self._current_mode = mode
                    return True
                else:
                    # No response, need to enter binary mode
                    print(f"[BusPirate] Not in binary mode, will attempt to enter it...")
                    self._client.close()
                    self._client = None
            except Exception as e:
                print(f"[BusPirate] Direct connection failed (expected): {e}")
                if self._client:
                    self._client.close()
                    self._client = None

            # Try 2: Enter binary mode via console
            if not self._enter_binary_mode(console_port):
                print(f"[BusPirate] Failed to enter binary mode")
                return False

            # Try 3: Connect to BPIO2 port after entering binary mode
            print(f"[BusPirate] Connecting to BPIO2 port after mode switch...")
            self._client = BPIOClient(
                port=bpio2_port,
                baudrate=3000000,
                timeout=2,
                debug=False
            )

            self._connected = True

            # Verify connection
            print(f"[BusPirate] Requesting status...")
            status = self._client.status_request()
            if status:
                mode = status.get('mode_current', 'unknown')
                fw_ver = f"{status['version_firmware_major']}.{status['version_firmware_minor']}"
                hw_ver = f"{status['version_hardware_major']} REV{status['version_hardware_minor']}"
                print(f"[BusPirate] Connected successfully!")
                print(f"[BusPirate] Firmware: v{fw_ver}")
                print(f"[BusPirate] Hardware: v{hw_ver}")
                print(f"[BusPirate] Current mode: {mode}")
                self._current_mode = mode
                return True
            else:
                print(f"[BusPirate] No response from status request after entering binary mode")
                self.disconnect()
                return False

        except Exception as e:
            print(f"[BusPirate] Connection failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def disconnect(self):
        """Disconnect from Bus Pirate."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._spi = None
        self._i2c = None
        self._connected = False

    def get_info(self) -> dict[str, Any]:
        """Get Bus Pirate status information."""
        if not self._connected or not self._client:
            return {"error": "Not connected"}

        status = self._client.status_request()
        return status if status else {"error": "Status request failed"}

    # --------------------------------------------------------------------------
    # SPI Interface
    # --------------------------------------------------------------------------

    def configure_spi(self, config: SPIConfig) -> bool:
        """Configure SPI interface."""
        if not self._connected or not self._client:
            return False

        # Create SPI interface if needed
        if not self._spi:
            self._spi = BPIOSPI(self._client)

        # Map config to BPIO2 parameters
        clock_polarity = bool((config.mode >> 1) & 1)  # CPOL
        clock_phase = bool(config.mode & 1)            # CPHA

        # Configure SPI mode with all parameters
        success = self._spi.configure(
            speed=config.speed_hz,
            clock_polarity=clock_polarity,
            clock_phase=clock_phase,
            chip_select_idle=config.cs_active_low,
        )

        if success:
            self._current_mode = "SPI"
            print(f"[BusPirate] SPI configured: {config.speed_hz}Hz, mode={config.mode}")

        return success

    def spi_transfer(self, write_data: bytes, read_len: int = 0) -> bytes:
        """Perform SPI transfer."""
        if not self._connected or not self._spi:
            return b''

        result = self._spi.transfer(write_data, read_bytes=read_len if read_len > 0 else None)
        return result if result else b''

    def spi_flash_read_id(self) -> bytes:
        """Read SPI flash JEDEC ID (0x9F command)."""
        if not self._connected or not self._spi:
            return b''
        return self.spi_transfer(b'\x9f', read_len=3)

    def spi_flash_read(self, address: int, length: int) -> bytes:
        """Read from SPI flash memory."""
        if not self._connected or not self._spi:
            return b''

        # Standard SPI flash read command: 0x03 + 24-bit address
        cmd = bytes([
            0x03,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF
        ])
        return self.spi_transfer(cmd, read_len=length)

    # --------------------------------------------------------------------------
    # I2C Interface
    # --------------------------------------------------------------------------

    def configure_i2c(self, config: I2CConfig) -> bool:
        """Configure I2C interface."""
        if not self._connected or not self._client:
            return False

        # Create I2C interface if needed
        if not self._i2c:
            self._i2c = BPIOI2C(self._client)

        # Configure I2C mode
        success = self._i2c.configure(
            speed=config.speed_hz,
            clock_stretch=False
        )

        if success:
            self._current_mode = "I2C"
            print(f"[BusPirate] I2C configured: {config.speed_hz}Hz")

        return success

    def i2c_write(self, address: int, data: bytes) -> bool:
        """Write data to I2C device."""
        if not self._connected or not self._i2c:
            return False

        # I2C address is 7-bit, shifted left with W bit (0)
        addr_byte = (address << 1) & 0xFE

        result = self._i2c.transfer(
            write_data=bytes([addr_byte]) + data,
            read_bytes=0
        )
        return result is not False

    def i2c_read(self, address: int, length: int) -> bytes:
        """Read data from I2C device."""
        if not self._connected or not self._i2c:
            return b''

        # I2C address with R bit (1)
        addr_byte = ((address << 1) | 1) & 0xFF

        result = self._i2c.transfer(
            write_data=bytes([addr_byte]),
            read_bytes=length
        )
        return result if result else b''

    def i2c_write_read(self, address: int, write_data: bytes, read_len: int) -> bytes:
        """Write then read from I2C device (repeated start)."""
        if not self._connected or not self._i2c:
            return b''

        # Full transaction with repeated start
        addr_byte = (address << 1) & 0xFE

        result = self._i2c.transfer(
            write_data=bytes([addr_byte]) + write_data,
            read_bytes=read_len
        )
        return result if result else b''

    def i2c_scan(self, start_addr: int = 0x08, end_addr: int = 0x77) -> list[int]:
        """Scan I2C bus for devices."""
        if not self._connected or not self._i2c:
            return []

        # Use official scan implementation
        found = self._i2c.scan(start_addr=start_addr, end_addr=end_addr)

        # Convert from their format (address << 1) back to 7-bit addresses
        addresses = list(set(addr >> 1 for addr in found))
        addresses.sort()

        return addresses

    # --------------------------------------------------------------------------
    # UART Interface
    # --------------------------------------------------------------------------

    def configure_uart(self, config: UARTConfig) -> bool:
        """Configure UART interface."""
        if not self._connected or not self._client:
            return False

        # Create UART wrapper if needed
        if not self._uart:
            self._uart = BPIOUART(self._client)

        # Map parity to boolean (UART uses boolean: True=even, False=none)
        parity = False
        if config.parity in ('E', 'O'):
            parity = True

        success = self._uart.configure(
            speed=config.baudrate,
            data_bits=config.data_bits,
            parity=parity,
            stop_bits=config.stop_bits,
            flow_control=False,
            signal_inversion=False
        )

        if success:
            self._current_mode = "UART"
            print(f"[BusPirate] UART configured: {config.baudrate} baud, {config.data_bits}{config.parity}{config.stop_bits}")

        return success

    def uart_write(self, data: bytes):
        """Write data to UART."""
        if not self._uart:
            return

        self._uart.write(list(data))

    def uart_read(self, length: int, timeout_ms: int = 1000) -> bytes:
        """Read data from UART."""
        if not self._uart:
            return b''

        result = self._uart.read(length)
        return result if result else b''

    # --------------------------------------------------------------------------
    # Target Device Scanning
    # --------------------------------------------------------------------------

    def scan_target(self, power_voltage_mv: int = 3300, power_current_ma: int = 300,
                    enable_pullups: bool = True) -> dict[str, Any]:
        """
        Power up and scan a target device for all available interfaces.

        This is a general-purpose function that:
        1. Enables PSU to power the target
        2. Scans I2C bus for devices
        3. Tests SPI for flash chips
        4. Reads pin voltages and IO states

        Args:
            power_voltage_mv: PSU voltage in millivolts (default: 3.3V)
            power_current_ma: PSU current limit in milliamps (default: 300mA)
            enable_pullups: Enable pull-up resistors for I2C (default: True)

        Returns:
            Dictionary with scan results:
            {
                'psu': {'enabled': bool, 'voltage_mv': int, 'current_ma': int},
                'i2c_devices': [list of 7-bit addresses],
                'spi_flash': {'detected': bool, 'id': bytes, 'manufacturer': int},
                'pin_voltages': {pin_name: voltage_mv},
                'io_status': {pin_name: {'direction': str, 'value': str}}
            }
        """
        import time

        if not self._connected or not self._client:
            return {'error': 'Not connected'}

        results = {}

        # 1. Enable PSU
        print(f"[Scan] Enabling PSU: {power_voltage_mv}mV, {power_current_ma}mA limit...")
        self.set_psu(enabled=True, voltage_mv=power_voltage_mv, current_ma=power_current_ma)
        time.sleep(0.5)  # Give target time to power up

        # Get PSU status
        info = self.get_info()
        psu_info = {
            'enabled': info.get('psu_enabled', False),
            'set_voltage_mv': info.get('psu_set_mv', 0),
            'measured_voltage_mv': info.get('psu_measured_mv', 0),
            'measured_current_ma': info.get('psu_measured_ma', 0),
            'over_current': info.get('psu_current_error', False)
        }
        results['psu'] = psu_info

        print(f"[Scan] PSU: {psu_info['measured_voltage_mv']}mV, {psu_info['measured_current_ma']}mA")
        if psu_info['over_current']:
            print("[Scan] ⚠️  PSU over-current detected!")

        # Wait for target to boot
        time.sleep(1)

        # 2. Scan I2C
        print(f"[Scan] Scanning I2C bus...")
        if enable_pullups:
            self.set_pullups(enabled=True)

        self.configure_i2c(I2CConfig(speed_hz=100_000))  # 100kHz standard mode
        i2c_devices = self.i2c_scan(start_addr=0x08, end_addr=0x77)
        results['i2c_devices'] = i2c_devices

        if i2c_devices:
            print(f"[Scan] Found {len(i2c_devices)} I2C device(s): {[hex(a) for a in i2c_devices]}")
        else:
            print(f"[Scan] No I2C devices found")

        # 3. Test SPI
        print(f"[Scan] Testing SPI interface...")
        self.configure_spi(SPIConfig(speed_hz=1_000_000, mode=0))
        flash_id = self.spi_flash_read_id()

        spi_detected = flash_id and flash_id != b'\x00\x00\x00' and flash_id != b'\xff\xff\xff'
        results['spi_flash'] = {
            'detected': spi_detected,
            'id': flash_id.hex() if flash_id else None,
            'manufacturer': flash_id[0] if flash_id and len(flash_id) > 0 else None,
            'device': flash_id[1:3].hex() if flash_id and len(flash_id) >= 3 else None
        }

        if spi_detected:
            print(f"[Scan] SPI flash detected: {flash_id.hex()}")
        else:
            print(f"[Scan] No SPI flash detected")

        # 4. Read pin voltages
        info = self.get_info()
        if 'adc_mv' in info and info['adc_mv']:
            pin_voltages = {}
            pin_labels = info.get('mode_pin_labels', [])

            # Map pin labels to voltages
            for i, label in enumerate(pin_labels):
                if i < len(info['adc_mv']):
                    pin_voltages[label] = info['adc_mv'][i]

            results['pin_voltages'] = pin_voltages
            print(f"[Scan] Pin voltages captured: {len(pin_voltages)} pins")

        # 5. IO status
        io_status = {}
        io_dir = info.get('io_direction', 0)
        io_val = info.get('io_value', 0)

        for i in range(8):
            direction = 'OUT' if (io_dir >> i) & 1 else 'IN'
            value = 'HIGH' if (io_val >> i) & 1 else 'LOW'
            io_status[f'IO{i}'] = {'direction': direction, 'value': value}

        results['io_status'] = io_status

        return results

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
        if not self._connected or not self._client:
            return False

        if enabled:
            return self._client.configuration_request(
                psu_enable=True,
                psu_set_mv=voltage_mv,
                psu_set_ma=current_ma
            )
        else:
            return self._client.configuration_request(
                psu_disable=True
            )

    def set_pullups(self, enabled: bool) -> bool:
        """Enable/disable internal pull-up resistors."""
        if not self._connected or not self._client:
            return False

        if enabled:
            return self._client.configuration_request(pullup_enable=True)
        else:
            return self._client.configuration_request(pullup_disable=True)


# Register this backend for buspirate device type
register_backend("buspirate", BusPirateBackend)
