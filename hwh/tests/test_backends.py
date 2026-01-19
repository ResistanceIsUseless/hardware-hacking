"""Tests for backend system."""

import pytest
from hwh.backends import (
    Backend, BusBackend, DebugBackend, GlitchBackend,
    SPIConfig, I2CConfig, UARTConfig, GlitchConfig,
    register_backend, get_backend, list_backends,
    BusProtocol, TriggerEdge
)
from hwh.detect import DeviceInfo


class MockBackend(Backend):
    """Mock backend for testing."""

    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self.connect_called = False
        self.disconnect_called = False

    def connect(self) -> bool:
        self.connect_called = True
        self._connected = True
        return True

    def disconnect(self):
        self.disconnect_called = True
        self._connected = False

    def get_info(self) -> dict:
        return {"mock": True}


class TestConfigs:
    """Test configuration dataclasses."""

    def test_spi_config_defaults(self):
        """Test SPIConfig default values."""
        config = SPIConfig()
        assert config.speed_hz == 1_000_000
        assert config.mode == 0
        assert config.bits_per_word == 8
        assert config.cs_active_low is True

    def test_spi_config_custom(self):
        """Test SPIConfig custom values."""
        config = SPIConfig(speed_hz=2_000_000, mode=3)
        assert config.speed_hz == 2_000_000
        assert config.mode == 3

    def test_i2c_config_defaults(self):
        """Test I2CConfig default values."""
        config = I2CConfig()
        assert config.speed_hz == 400_000
        assert config.address_bits == 7

    def test_uart_config_defaults(self):
        """Test UARTConfig default values."""
        config = UARTConfig()
        assert config.baudrate == 115200
        assert config.data_bits == 8
        assert config.parity == "N"
        assert config.stop_bits == 1

    def test_glitch_config_defaults(self):
        """Test GlitchConfig default values."""
        config = GlitchConfig()
        assert config.width_ns == 100
        assert config.offset_ns == 0
        assert config.repeat == 1
        assert config.trigger_channel is None
        assert config.trigger_edge == TriggerEdge.FALLING


class TestBackendRegistry:
    """Test backend registration and retrieval."""

    def test_register_backend(self):
        """Test registering a backend."""
        register_backend("mock", MockBackend)

        backends = list_backends()
        assert "mock" in backends
        assert backends["mock"] == MockBackend

    def test_get_backend(self):
        """Test getting a backend instance."""
        register_backend("mock", MockBackend)

        device = DeviceInfo(
            name="Mock Device",
            device_type="mock",
            capabilities=[]
        )

        backend = get_backend(device)
        assert backend is not None
        assert isinstance(backend, MockBackend)
        assert backend.device == device

    def test_get_backend_unknown_type(self):
        """Test getting backend for unknown type returns None."""
        device = DeviceInfo(
            name="Unknown",
            device_type="nonexistent",
            capabilities=[]
        )

        backend = get_backend(device)
        assert backend is None


class TestBackendContextManager:
    """Test backend context manager protocol."""

    def test_context_manager(self):
        """Test backend as context manager."""
        register_backend("mock", MockBackend)

        device = DeviceInfo(
            name="Mock Device",
            device_type="mock",
            capabilities=[]
        )

        backend = get_backend(device)

        with backend as b:
            assert b.connect_called
            assert b.connected

        assert backend.disconnect_called
        assert not backend.connected


class TestEnums:
    """Test enum types."""

    def test_bus_protocol_enum(self):
        """Test BusProtocol enum."""
        assert BusProtocol.SPI
        assert BusProtocol.I2C
        assert BusProtocol.UART
        assert BusProtocol.JTAG
        assert BusProtocol.SWD

    def test_trigger_edge_enum(self):
        """Test TriggerEdge enum."""
        assert TriggerEdge.RISING
        assert TriggerEdge.FALLING
        assert TriggerEdge.EITHER


class TestGlitchSweep:
    """Test glitch sweep functionality."""

    def test_glitch_sweep_basic(self):
        """Test basic glitch sweep calculation."""
        # Create mock glitch backend
        class MockGlitchBackend(GlitchBackend):
            def __init__(self, device):
                super().__init__(device)
                self.glitches = []

            def connect(self):
                self._connected = True
                return True

            def disconnect(self):
                self._connected = False

            def get_info(self):
                return {}

            def configure_glitch(self, config):
                return True

            def arm(self):
                return True

            def trigger(self):
                self.glitches.append(True)
                return True

            def disarm(self):
                return True

        device = DeviceInfo(
            name="Mock Glitcher",
            device_type="mock_glitch",
            capabilities=["glitch"]
        )

        backend = MockGlitchBackend(device)

        results = backend.run_glitch_sweep(
            width_range=(100, 200),
            width_step=50,
            offset_range=(0, 100),
            offset_step=50,
            attempts_per_setting=2
        )

        # Should be: 3 widths * 3 offsets * 2 attempts = 18 results
        assert len(results) == 18
        assert len(backend.glitches) == 18

        # Check result structure
        assert "width_ns" in results[0]
        assert "offset_ns" in results[0]
        assert "attempt" in results[0]
