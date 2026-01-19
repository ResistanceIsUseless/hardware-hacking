"""Pytest configuration and fixtures."""

import pytest
from hwh.detect import DeviceInfo


@pytest.fixture
def mock_stlink_device():
    """Mock ST-Link device for testing."""
    return DeviceInfo(
        name="ST-Link V2",
        device_type="stlink",
        port="/dev/ttyACM0",
        vid=0x0483,
        pid=0x3748,
        serial="12345678",
        capabilities=["swd", "jtag", "debug"]
    )


@pytest.fixture
def mock_buspirate_device():
    """Mock Bus Pirate device for testing."""
    return DeviceInfo(
        name="Bus Pirate 5",
        device_type="buspirate",
        port="/dev/ttyACM1",
        vid=0x2047,
        pid=0x0900,
        serial="BP5-123",
        capabilities=["spi", "i2c", "uart", "1wire", "jtag", "psu"]
    )


@pytest.fixture
def mock_tigard_device():
    """Mock Tigard device for testing."""
    return DeviceInfo(
        name="Tigard",
        device_type="tigard",
        port="/dev/ttyUSB0",
        vid=0x0403,
        pid=0x6010,
        capabilities=["spi", "i2c", "uart", "jtag", "swd"]
    )


@pytest.fixture
def mock_bolt_device():
    """Mock Curious Bolt device for testing."""
    return DeviceInfo(
        name="Curious Bolt",
        device_type="bolt",
        port="/dev/ttyACM2",
        vid=0x2E8A,
        pid=0x000A,
        capabilities=["glitch", "logic", "dpa"]
    )
