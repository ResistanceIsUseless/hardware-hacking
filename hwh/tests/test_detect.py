"""Tests for device detection."""

import pytest
from hwh.detect import DeviceInfo, detect, list_devices, _deduplicate_devices


class TestDeviceInfo:
    """Test DeviceInfo dataclass."""

    def test_device_info_creation(self):
        """Test creating a DeviceInfo object."""
        device = DeviceInfo(
            name="Test Device",
            device_type="test",
            port="/dev/ttyACM0",
            vid=0x1234,
            pid=0x5678,
            capabilities=["spi", "i2c"]
        )

        assert device.name == "Test Device"
        assert device.device_type == "test"
        assert device.port == "/dev/ttyACM0"
        assert device.vid == 0x1234
        assert device.pid == 0x5678
        assert "spi" in device.capabilities
        assert "i2c" in device.capabilities


class TestDeduplication:
    """Test device deduplication logic."""

    def test_deduplicate_by_serial(self):
        """Devices with same serial number should be deduplicated."""
        devices = [
            DeviceInfo(
                name="Device 1",
                device_type="test",
                serial="ABC123",
                vid=0x1234,
                pid=0x5678,
                port="/dev/ttyACM0"
            ),
            DeviceInfo(
                name="Device 1",
                device_type="test",
                serial="ABC123",
                vid=0x1234,
                pid=0x5678,
                usb_path="1:2"
            ),
        ]

        result = _deduplicate_devices(devices)
        assert len(result) == 1
        # Should merge port and usb_path
        assert result[0].port == "/dev/ttyACM0"
        assert result[0].usb_path == "1:2"

    def test_deduplicate_different_devices(self):
        """Different devices should not be deduplicated."""
        devices = [
            DeviceInfo(
                name="Device 1",
                device_type="test1",
                serial="ABC123",
                vid=0x1234,
                pid=0x5678
            ),
            DeviceInfo(
                name="Device 2",
                device_type="test2",
                serial="DEF456",
                vid=0x9ABC,
                pid=0xDEF0
            ),
        ]

        result = _deduplicate_devices(devices)
        assert len(result) == 2


class TestDetection:
    """Test device detection functions."""

    def test_detect_returns_dict(self):
        """detect() should return a dictionary."""
        devices = detect(identify_unknown=False)
        assert isinstance(devices, dict)

    def test_list_devices_returns_list(self):
        """list_devices() should return a list."""
        devices = list_devices(include_unknown=False)
        assert isinstance(devices, list)

    def test_detect_keys_unique(self):
        """detect() should handle multiple devices of same type with unique keys."""
        # This is a functional test - can only verify the structure
        devices = detect(identify_unknown=False)

        # Check that keys are strings
        for key in devices.keys():
            assert isinstance(key, str)

        # Check that values are DeviceInfo
        for device in devices.values():
            assert isinstance(device, DeviceInfo)


class TestKnownDevices:
    """Test known device database."""

    def test_stlink_vid_pid(self):
        """Test ST-Link VID/PID is in database."""
        from hwh.detect import KNOWN_USB_DEVICES

        # ST-Link V2
        assert (0x0483, 0x3748) in KNOWN_USB_DEVICES
        name, dtype, caps = KNOWN_USB_DEVICES[(0x0483, 0x3748)]
        assert dtype == "stlink"
        assert "swd" in caps

    def test_buspirate_vid_pid(self):
        """Test Bus Pirate VID/PID is in database."""
        from hwh.detect import KNOWN_USB_DEVICES

        # Bus Pirate 5
        assert (0x2047, 0x0900) in KNOWN_USB_DEVICES
        name, dtype, caps = KNOWN_USB_DEVICES[(0x2047, 0x0900)]
        assert dtype == "buspirate"
        assert "spi" in caps

    def test_rp2040_requires_identification(self):
        """RP2040 devices should be marked as unknown pending identification."""
        from hwh.detect import KNOWN_USB_DEVICES

        # RP2040 devices use same VID:PID
        if (0x2E8A, 0x000A) in KNOWN_USB_DEVICES:
            name, dtype, caps = KNOWN_USB_DEVICES[(0x2E8A, 0x000A)]
            assert dtype == "rp2040_unknown"
