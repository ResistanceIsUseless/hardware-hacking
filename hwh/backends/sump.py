"""
SUMP Protocol Implementation for Logic Analyzers

SUMP (Simple Universal Multi-channel Protocol) is the open protocol used by
sigrok/PulseView and many logic analyzers including Bus Pirate and some modes
of Curious Bolt.

Protocol reference:
- https://www.sump.org/projects/analyzer/protocol/
- https://sigrok.org/wiki/Openbench_Logic_Sniffer

Commands:
- 0x00: Reset
- 0x01: Run (arm and wait for trigger)
- 0x02: ID (returns "1ALS" for SUMP devices)
- 0x11: Get metadata
- 0x80-0x9F: Set trigger mask/values/config
- 0xC0-0xC4: Set divider and read count
- 0x81: Set flags (channels, demux, etc)
"""

import time
import struct
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from enum import IntEnum


class SUMPCommand(IntEnum):
    """SUMP protocol commands"""
    RESET = 0x00
    RUN = 0x01
    ID = 0x02
    METADATA = 0x11
    XON = 0x13
    XOFF = 0x11

    # Trigger commands (short)
    SET_TRIGGER_MASK_0 = 0xC0
    SET_TRIGGER_VALUE_0 = 0xC1
    SET_TRIGGER_CONFIG_0 = 0xC2

    # Long commands (5 bytes)
    SET_DIVIDER = 0x80
    SET_READ_DELAY_COUNT = 0x81
    SET_FLAGS = 0x82


class SUMPFlags(IntEnum):
    """SUMP flag bits"""
    DEMUX = 0x01           # Enable demux mode (double sample rate, half channels)
    FILTER = 0x02          # Enable noise filter
    CHANNEL_GROUP_0 = 0x04  # Disable channel group 0 (ch 0-7)
    CHANNEL_GROUP_1 = 0x08  # Disable channel group 1 (ch 8-15)
    CHANNEL_GROUP_2 = 0x10  # Disable channel group 2 (ch 16-23)
    CHANNEL_GROUP_3 = 0x20  # Disable channel group 3 (ch 24-31)
    EXTERNAL_CLOCK = 0x40  # Use external clock
    INVERTED_CLOCK = 0x80  # Invert clock


@dataclass
class SUMPConfig:
    """SUMP capture configuration"""
    sample_rate: int = 1_000_000      # Sample rate in Hz
    sample_count: int = 8192          # Number of samples to capture
    channels: int = 8                  # Number of channels (8, 16, 24, 32)
    trigger_mask: int = 0             # Which bits to match for trigger
    trigger_value: int = 0            # Expected values for trigger bits
    trigger_delay: int = 0            # Samples to delay after trigger
    demux: bool = False               # Demux mode (2x rate, half channels)
    base_clock: int = 100_000_000     # Device's base clock frequency


@dataclass
class SUMPCapture:
    """Captured logic data from SUMP device"""
    channels: int = 8
    sample_rate: int = 1_000_000
    samples: List[List[int]] = field(default_factory=list)  # Per-channel sample lists
    trigger_position: int = 0
    raw_data: bytes = b''


class SUMPClient:
    """
    SUMP protocol client for logic analyzers.

    Works with:
    - Bus Pirate 5/6 in SUMP mode
    - Open Bench Logic Sniffer
    - Sigrok-compatible devices
    - Curious Bolt (some modes)
    """

    SUMP_ID = b'1ALS'  # Standard SUMP identification response

    def __init__(self, serial_port, timeout: float = 2.0, debug: bool = False):
        """
        Initialize SUMP client.

        Args:
            serial_port: pyserial Serial instance (already opened)
            timeout: Communication timeout in seconds
            debug: Enable debug output
        """
        self._serial = serial_port
        self._timeout = timeout
        self._debug = debug
        self._config = SUMPConfig()
        self._metadata = {}

    def _log(self, msg: str) -> None:
        """Debug logging"""
        if self._debug:
            print(f"[SUMP] {msg}")

    def _send_command(self, cmd: int, data: bytes = b'') -> None:
        """Send a SUMP command"""
        if data:
            # Long command (5 bytes total)
            self._serial.write(bytes([cmd]) + data)
            self._log(f"TX: {cmd:02X} {data.hex()}")
        else:
            # Short command (1 byte)
            self._serial.write(bytes([cmd]))
            self._log(f"TX: {cmd:02X}")

    def _read_response(self, length: int, timeout: Optional[float] = None) -> bytes:
        """Read response from device"""
        if timeout is None:
            timeout = self._timeout

        old_timeout = self._serial.timeout
        self._serial.timeout = timeout

        try:
            data = self._serial.read(length)
            self._log(f"RX: {data.hex() if data else '(empty)'}")
            return data
        finally:
            self._serial.timeout = old_timeout

    def reset(self) -> bool:
        """Reset the SUMP device"""
        # Send reset command 5 times (per SUMP spec)
        for _ in range(5):
            self._send_command(SUMPCommand.RESET)
        time.sleep(0.1)

        # Flush input buffer
        self._serial.reset_input_buffer()
        return True

    def identify(self) -> Tuple[bool, str]:
        """
        Send ID command and check for SUMP device.

        Returns:
            (success, id_string)
        """
        self._serial.reset_input_buffer()
        self._send_command(SUMPCommand.ID)

        response = self._read_response(4, timeout=0.5)

        if response == self.SUMP_ID:
            return True, response.decode('ascii')
        elif len(response) >= 4:
            return True, response[:4].decode('ascii', errors='ignore')
        else:
            return False, ""

    def get_metadata(self) -> dict:
        """
        Request device metadata (extended SUMP protocol).

        Returns dictionary with device capabilities.
        """
        self._serial.reset_input_buffer()
        self._send_command(SUMPCommand.METADATA)

        metadata = {}

        # Read metadata tokens until we get 0x00
        try:
            while True:
                token = self._serial.read(1)
                if not token or token == b'\x00':
                    break

                token_type = token[0]

                if token_type & 0x80:
                    # String token
                    string_data = b''
                    while True:
                        char = self._serial.read(1)
                        if not char or char == b'\x00':
                            break
                        string_data += char

                    if token_type == 0x01:
                        metadata['device_name'] = string_data.decode('ascii', errors='ignore')
                    elif token_type == 0x02:
                        metadata['firmware_version'] = string_data.decode('ascii', errors='ignore')
                    elif token_type == 0x03:
                        metadata['protocol_version'] = string_data.decode('ascii', errors='ignore')
                else:
                    # Numeric token (4 bytes, big endian)
                    num_data = self._serial.read(4)
                    if len(num_data) == 4:
                        value = struct.unpack('>I', num_data)[0]

                        if token_type == 0x20:
                            metadata['num_probes'] = value
                        elif token_type == 0x21:
                            metadata['sample_memory'] = value
                        elif token_type == 0x22:
                            metadata['dynamic_memory'] = value
                        elif token_type == 0x23:
                            metadata['max_sample_rate'] = value
                        elif token_type == 0x24:
                            metadata['protocol_flags'] = value

        except Exception as e:
            self._log(f"Metadata read error: {e}")

        self._metadata = metadata
        return metadata

    def configure(self, config: SUMPConfig) -> bool:
        """
        Configure capture parameters.

        Args:
            config: SUMPConfig with desired settings
        """
        self._config = config

        # Calculate clock divider
        # divider = (base_clock / sample_rate) - 1
        divider = (config.base_clock // config.sample_rate) - 1
        if divider < 0:
            divider = 0
        if divider > 0xFFFFFF:
            divider = 0xFFFFFF

        # Calculate read and delay count
        # read_count = (samples / 4) - 1
        # delay_count = (delay_samples / 4) - 1
        read_count = (config.sample_count // 4) - 1
        delay_count = (config.trigger_delay // 4) if config.trigger_delay else 0

        self._log(f"Configure: rate={config.sample_rate}, samples={config.sample_count}")
        self._log(f"  divider={divider}, read_count={read_count}, delay_count={delay_count}")

        # Set clock divider (24-bit)
        divider_data = struct.pack('<I', divider)[:3] + b'\x00'
        self._send_command(SUMPCommand.SET_DIVIDER, divider_data)

        # Set read and delay count
        count_data = struct.pack('<HH', read_count & 0xFFFF, delay_count & 0xFFFF)
        self._send_command(SUMPCommand.SET_READ_DELAY_COUNT, count_data)

        # Set flags
        flags = 0
        if config.demux:
            flags |= SUMPFlags.DEMUX

        # Disable unused channel groups
        if config.channels <= 8:
            flags |= SUMPFlags.CHANNEL_GROUP_1 | SUMPFlags.CHANNEL_GROUP_2 | SUMPFlags.CHANNEL_GROUP_3
        elif config.channels <= 16:
            flags |= SUMPFlags.CHANNEL_GROUP_2 | SUMPFlags.CHANNEL_GROUP_3
        elif config.channels <= 24:
            flags |= SUMPFlags.CHANNEL_GROUP_3

        flags_data = struct.pack('<I', flags)
        self._send_command(SUMPCommand.SET_FLAGS, flags_data)

        # Set trigger (stage 0 only for simple trigger)
        if config.trigger_mask:
            # Trigger mask - which bits to check
            mask_data = struct.pack('<I', config.trigger_mask)
            self._send_command(SUMPCommand.SET_TRIGGER_MASK_0, mask_data)

            # Trigger value - expected values
            value_data = struct.pack('<I', config.trigger_value)
            self._send_command(SUMPCommand.SET_TRIGGER_VALUE_0, value_data)

            # Trigger config - enable trigger
            # Bits: [31:28] delay, [27:24] level, [23:16] channel, [15:8] serial, [3] start, [2:0] serial config
            trig_config = 0x08  # Start capture on trigger (bit 3)
            config_data = struct.pack('<I', trig_config)
            self._send_command(SUMPCommand.SET_TRIGGER_CONFIG_0, config_data)
        else:
            # No trigger - immediate capture
            config_data = struct.pack('<I', 0)
            self._send_command(SUMPCommand.SET_TRIGGER_CONFIG_0, config_data)

        return True

    def capture(self, timeout: Optional[float] = None) -> Optional[SUMPCapture]:
        """
        Start capture and wait for data.

        Args:
            timeout: Max time to wait for capture (includes trigger wait)

        Returns:
            SUMPCapture with sample data, or None on error
        """
        if timeout is None:
            timeout = 10.0  # Default 10 second timeout

        # Calculate expected data size
        bytes_per_sample = (self._config.channels + 7) // 8
        expected_bytes = self._config.sample_count * bytes_per_sample

        self._log(f"Starting capture: {expected_bytes} bytes expected")

        # Flush input
        self._serial.reset_input_buffer()

        # Send RUN command
        self._send_command(SUMPCommand.RUN)

        # Read sample data
        start_time = time.time()
        raw_data = b''

        while len(raw_data) < expected_bytes:
            if time.time() - start_time > timeout:
                self._log(f"Capture timeout ({len(raw_data)}/{expected_bytes} bytes)")
                if len(raw_data) == 0:
                    return None
                break

            chunk = self._serial.read(min(4096, expected_bytes - len(raw_data)))
            if chunk:
                raw_data += chunk
                self._log(f"Read {len(chunk)} bytes, total {len(raw_data)}/{expected_bytes}")

        self._log(f"Capture complete: {len(raw_data)} bytes")

        # Parse raw data into channels
        return self._parse_capture(raw_data)

    def _parse_capture(self, raw_data: bytes) -> SUMPCapture:
        """Parse raw SUMP data into channel samples"""
        channels = self._config.channels
        bytes_per_sample = (channels + 7) // 8

        # Initialize channel arrays
        channel_samples = [[] for _ in range(channels)]

        # SUMP data is in reverse order (newest first)
        # and samples are packed LSB first
        sample_count = len(raw_data) // bytes_per_sample

        for i in range(sample_count - 1, -1, -1):  # Reverse order
            offset = i * bytes_per_sample
            sample_bytes = raw_data[offset:offset + bytes_per_sample]

            # Convert bytes to sample value
            sample = 0
            for j, b in enumerate(sample_bytes):
                sample |= b << (j * 8)

            # Extract each channel bit
            for ch in range(channels):
                bit = (sample >> ch) & 1
                channel_samples[ch].append(bit)

        # Find trigger position (look for trigger pattern)
        trigger_pos = 0
        if self._config.trigger_mask:
            mask = self._config.trigger_mask
            value = self._config.trigger_value

            for i in range(min(len(channel_samples[0]), sample_count)):
                sample = 0
                for ch in range(min(channels, 8)):
                    if i < len(channel_samples[ch]):
                        sample |= channel_samples[ch][i] << ch

                if (sample & mask) == value:
                    trigger_pos = i
                    break

        return SUMPCapture(
            channels=channels,
            sample_rate=self._config.sample_rate,
            samples=channel_samples,
            trigger_position=trigger_pos,
            raw_data=raw_data
        )

    def abort(self) -> None:
        """Abort current capture"""
        self.reset()


def capture_logic(
    serial_port,
    sample_rate: int = 1_000_000,
    sample_count: int = 8192,
    channels: int = 8,
    trigger_channel: Optional[int] = None,
    trigger_edge: str = "rising",
    timeout: float = 10.0,
    debug: bool = False
) -> Optional[SUMPCapture]:
    """
    Convenience function to capture logic data.

    Args:
        serial_port: pyserial Serial instance
        sample_rate: Sample rate in Hz
        sample_count: Number of samples to capture
        channels: Number of channels (8, 16, 24, 32)
        trigger_channel: Channel to trigger on (None for immediate)
        trigger_edge: "rising" or "falling"
        timeout: Capture timeout in seconds
        debug: Enable debug output

    Returns:
        SUMPCapture with data, or None on error
    """
    client = SUMPClient(serial_port, debug=debug)

    # Reset device
    client.reset()

    # Check for SUMP device
    success, device_id = client.identify()
    if not success:
        print(f"[SUMP] Device not responding (got: {device_id})")
        return None

    # Build config
    config = SUMPConfig(
        sample_rate=sample_rate,
        sample_count=sample_count,
        channels=channels,
    )

    # Set trigger if specified
    if trigger_channel is not None and 0 <= trigger_channel < channels:
        config.trigger_mask = 1 << trigger_channel
        if trigger_edge == "rising":
            config.trigger_value = 1 << trigger_channel  # Wait for high
        else:
            config.trigger_value = 0  # Wait for low

    # Configure and capture
    client.configure(config)
    return client.capture(timeout=timeout)
