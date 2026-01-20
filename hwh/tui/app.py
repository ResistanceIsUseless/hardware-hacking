"""
Universal TUI for hwh - Hardware Hacking Tool

A single interface that adapts to whatever device is connected.
Works with Bus Pirate, Curious Bolt, FaultyCat, ST-Link, Tigard, etc.

Design inspired by glitch-o-bolt by 0xRoM, but generalized for all tools.
"""

import asyncio
from typing import Optional, Dict, Any, List
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Switch, Input, Log, TabbedContent, TabPane, DataTable
from textual.messages import Message

from ..detect import detect, DeviceInfo
from ..backends import get_backend, Backend, BusBackend, DebugBackend, GlitchBackend


class DeviceMessage(Message):
    """Message sent when device selection changes"""
    def __init__(self, device: Optional[DeviceInfo]):
        super().__init__()
        self.device = device


class SerialDataMessage(Message):
    """Message sent when serial data is received"""
    def __init__(self, data: str):
        super().__init__()
        self.data = data


class HwhApp(App):
    """
    Universal TUI that adapts to connected hardware

    Features:
    - Auto-detects all connected devices
    - Shows only relevant controls based on device capabilities
    - Provides tabs for different protocols (SPI, I2C, UART, Glitch, etc.)
    - Real-time serial monitoring
    - Interactive parameter adjustment
    - Command history
    """

    CSS = """
    Screen {
        background: $surface;
    }

    #header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        content-align: center middle;
    }

    #device-selector {
        dock: top;
        height: 3;
        background: $panel;
        padding: 0 1;
    }

    .main-content {
        height: 1fr;
    }

    .sidebar {
        width: 30;
        dock: left;
        background: $panel;
    }

    .log-container {
        height: 1fr;
        border: solid $accent;
    }

    .input-container {
        dock: bottom;
        height: 3;
        background: $panel;
    }

    .param-grid {
        grid-size: 3;
        grid-rows: auto;
        padding: 1;
    }

    .btn {
        width: 8;
        margin: 0 1;
    }

    .btn-wide {
        width: 100%;
        margin: 1 0;
    }

    Input {
        margin: 1;
    }

    DataTable {
        height: auto;
        margin: 1;
    }
    """

    TITLE = "hwh - Universal Hardware Hacking Tool"

    def __init__(self):
        super().__init__()
        self.devices: Dict[str, DeviceInfo] = {}
        self.current_device: Optional[DeviceInfo] = None
        self.backend: Optional[Backend] = None
        self.serial_buffer = ""

    async def on_ready(self) -> None:
        """Called when app is ready"""
        # Detect devices
        self.devices = detect()

        if self.devices:
            # Auto-select first device
            first_key = list(self.devices.keys())[0]
            await self.select_device(first_key)
        else:
            self.notify("No devices detected!", severity="warning")

    async def select_device(self, device_key: str) -> None:
        """Switch to a different device"""
        device = self.devices.get(device_key)
        if not device:
            return

        # Disconnect old backend
        if self.backend:
            try:
                self.backend.disconnect()
            except:
                pass

        # Create new backend
        self.current_device = device
        self.backend = get_backend(device)

        try:
            self.backend.connect()
            self.notify(f"Connected to {device.name}", severity="information")
            self.post_message(DeviceMessage(device))
        except Exception as e:
            self.notify(f"Failed to connect: {e}", severity="error")

    def compose(self) -> ComposeResult:
        """Build the UI"""
        # Header
        yield Static(self.TITLE, id="header")

        # Device selector
        with Horizontal(id="device-selector"):
            yield Static("Device:", classes="label")

            for key, device in self.devices.items():
                caps_str = ", ".join(device.capabilities[:3])  # Show first 3 capabilities
                yield Button(
                    f"{device.name} ({caps_str})",
                    id=f"select-{key}",
                    classes="device-btn"
                )

        # Main content area with tabs
        with Container(classes="main-content"):
            # Sidebar with common controls
            with Vertical(classes="sidebar"):
                yield Static("Device Info", classes="sidebar-title")

                # Device info table
                device_table = DataTable(id="device-info", show_header=False)
                device_table.add_columns("Property", "Value")
                yield device_table

                # Connection controls
                with Vertical(classes="connection-controls"):
                    yield Static("Connection", classes="section-title")
                    yield Button("Connect", id="btn-connect", classes="btn-wide")
                    yield Button("Disconnect", id="btn-disconnect", classes="btn-wide")

            # Tabbed content area - adapts based on device capabilities
            with TabbedContent(id="main-tabs"):
                # Always show Console tab
                with TabPane("Console", id="tab-console"):
                    self.log_widget = Log(id="console-log")
                    yield self.log_widget

                    with Horizontal(classes="input-container"):
                        yield Static("$> ", classes="input-prompt")
                        yield Input(
                            placeholder="Enter command...",
                            id="command-input",
                            classes="command-input"
                        )

                # SPI tab (if device supports SPI)
                with TabPane("SPI", id="tab-spi"):
                    yield self._build_spi_controls()

                # I2C tab (if device supports I2C)
                with TabPane("I2C", id="tab-i2c"):
                    yield self._build_i2c_controls()

                # UART tab (if device supports UART)
                with TabPane("UART", id="tab-uart"):
                    yield self._build_uart_controls()

                # Glitch tab (if device supports glitching)
                with TabPane("Glitch", id="tab-glitch"):
                    yield self._build_glitch_controls()

                # Debug tab (if device supports debug)
                with TabPane("Debug", id="tab-debug"):
                    yield self._build_debug_controls()

    def _build_spi_controls(self) -> ComposeResult:
        """Build SPI operation controls"""
        with Vertical():
            yield Static("SPI Configuration", classes="section-title")

            with Grid(classes="param-grid"):
                yield Static("Speed (Hz):")
                yield Input(value="1000000", id="spi-speed")
                yield Static("")

                yield Static("Mode:")
                yield Input(value="0", id="spi-mode")
                yield Static("(0-3)")

                yield Static("Bits/Word:")
                yield Input(value="8", id="spi-bits")
                yield Static("")

            yield Button("Configure SPI", id="btn-spi-configure", classes="btn-wide")

            yield Static("Operations", classes="section-title")

            with Vertical():
                yield Button("Read Flash ID", id="btn-spi-id", classes="btn-wide")
                yield Button("Dump Flash", id="btn-spi-dump", classes="btn-wide")
                yield Button("Erase Sector", id="btn-spi-erase", classes="btn-wide")
                yield Button("Write Flash", id="btn-spi-write", classes="btn-wide")

    def _build_i2c_controls(self) -> ComposeResult:
        """Build I2C operation controls"""
        with Vertical():
            yield Static("I2C Configuration", classes="section-title")

            with Grid(classes="param-grid"):
                yield Static("Speed (Hz):")
                yield Input(value="100000", id="i2c-speed")
                yield Static("(100kHz)")

                yield Static("Address Bits:")
                yield Input(value="7", id="i2c-addr-bits")
                yield Static("(7 or 10)")

            yield Button("Configure I2C", id="btn-i2c-configure", classes="btn-wide")

            yield Static("Operations", classes="section-title")

            with Vertical():
                yield Button("Scan Bus", id="btn-i2c-scan", classes="btn-wide")

                with Horizontal():
                    yield Static("Address:")
                    yield Input(value="0x50", id="i2c-addr")

                yield Button("Read Byte", id="btn-i2c-read", classes="btn-wide")
                yield Button("Write Byte", id="btn-i2c-write", classes="btn-wide")

    def _build_uart_controls(self) -> ComposeResult:
        """Build UART operation controls"""
        with Vertical():
            yield Static("UART Configuration", classes="section-title")

            with Grid(classes="param-grid"):
                yield Static("Baud Rate:")
                yield Input(value="115200", id="uart-baud")
                yield Static("")

                yield Static("Data Bits:")
                yield Input(value="8", id="uart-data-bits")
                yield Static("(5-8)")

                yield Static("Parity:")
                yield Input(value="N", id="uart-parity")
                yield Static("(N/E/O)")

                yield Static("Stop Bits:")
                yield Input(value="1", id="uart-stop-bits")
                yield Static("(1-2)")

            yield Button("Configure UART", id="btn-uart-configure", classes="btn-wide")

            yield Static("Operations", classes="section-title")

            with Vertical():
                yield Button("Enable RX Monitor", id="btn-uart-monitor", classes="btn-wide")

                with Horizontal():
                    yield Static("TX:")
                    yield Input(placeholder="Data to send...", id="uart-tx-data")

                yield Button("Send", id="btn-uart-send", classes="btn-wide")

    def _build_glitch_controls(self) -> ComposeResult:
        """Build glitching operation controls"""
        with Vertical():
            yield Static("Glitch Parameters", classes="section-title")

            with Grid(classes="param-grid"):
                yield Static("Width (ns):")
                yield Input(value="350", id="glitch-width")
                yield Static("")

                yield Static("Offset (ns):")
                yield Input(value="0", id="glitch-offset")
                yield Static("")

                yield Static("Repeat:")
                yield Input(value="1", id="glitch-repeat")
                yield Static("times")

            yield Button("Configure Glitch", id="btn-glitch-configure", classes="btn-wide")

            yield Static("Operations", classes="section-title")

            with Vertical():
                yield Button("Single Glitch", id="btn-glitch-single", classes="btn-wide")
                yield Switch(id="glitch-continuous", value=False)
                yield Static("Continuous Glitching")

                yield Static("Parameter Sweep", classes="section-title")

                with Grid(classes="param-grid"):
                    yield Static("Width Min:")
                    yield Input(value="50", id="glitch-width-min")
                    yield Static("ns")

                    yield Static("Width Max:")
                    yield Input(value="1000", id="glitch-width-max")
                    yield Static("ns")

                    yield Static("Width Step:")
                    yield Input(value="50", id="glitch-width-step")
                    yield Static("ns")

                yield Button("Start Sweep", id="btn-glitch-sweep", classes="btn-wide")

    def _build_debug_controls(self) -> ComposeResult:
        """Build debug/SWD/JTAG operation controls"""
        with Vertical():
            yield Static("Debug Configuration", classes="section-title")

            with Vertical():
                yield Button("Connect Target", id="btn-debug-connect", classes="btn-wide")
                yield Button("Reset Target", id="btn-debug-reset", classes="btn-wide")
                yield Button("Halt Target", id="btn-debug-halt", classes="btn-wide")
                yield Button("Resume Target", id="btn-debug-resume", classes="btn-wide")

            yield Static("Memory Operations", classes="section-title")

            with Grid(classes="param-grid"):
                yield Static("Address:")
                yield Input(value="0x08000000", id="debug-addr")
                yield Static("")

                yield Static("Size:")
                yield Input(value="0x1000", id="debug-size")
                yield Static("bytes")

            with Vertical():
                yield Button("Read Memory", id="btn-debug-read", classes="btn-wide")
                yield Button("Write Memory", id="btn-debug-write", classes="btn-wide")
                yield Button("Dump Firmware", id="btn-debug-dump", classes="btn-wide")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id

        # Device selection buttons
        if button_id and button_id.startswith("select-"):
            device_key = button_id.replace("select-", "")
            asyncio.create_task(self.select_device(device_key))
            return

        # Connection buttons
        if button_id == "btn-connect":
            if self.backend:
                try:
                    self.backend.connect()
                    self.log("Connected")
                except Exception as e:
                    self.log(f"Error: {e}")

        elif button_id == "btn-disconnect":
            if self.backend:
                try:
                    self.backend.disconnect()
                    self.log("Disconnected")
                except Exception as e:
                    self.log(f"Error: {e}")

        # SPI buttons
        elif button_id == "btn-spi-id":
            self.handle_spi_read_id()
        elif button_id == "btn-spi-dump":
            self.handle_spi_dump()

        # I2C buttons
        elif button_id == "btn-i2c-scan":
            self.handle_i2c_scan()

        # Glitch buttons
        elif button_id == "btn-glitch-single":
            self.handle_glitch_single()
        elif button_id == "btn-glitch-sweep":
            self.handle_glitch_sweep()

        # Add more button handlers as needed...

    def log(self, message: str) -> None:
        """Add message to console log"""
        self.log_widget.write_line(message)

    # Handler methods (implement based on backend capabilities)

    def handle_spi_read_id(self) -> None:
        """Read SPI flash ID"""
        if not isinstance(self.backend, BusBackend):
            self.log("Device does not support SPI")
            return

        try:
            with self.backend:
                # Send 0x9F command to read JEDEC ID
                flash_id = self.backend.spi_transfer(b'\x9f', read_len=3)
                self.log(f"Flash ID: {flash_id.hex()}")
        except Exception as e:
            self.log(f"Error: {e}")

    def handle_spi_dump(self) -> None:
        """Dump SPI flash to file"""
        # Implementation details...
        self.log("SPI dump not yet implemented")

    def handle_i2c_scan(self) -> None:
        """Scan I2C bus for devices"""
        if not isinstance(self.backend, BusBackend):
            self.log("Device does not support I2C")
            return

        self.log("Scanning I2C bus...")
        # Implementation details...
        self.log("I2C scan not yet implemented")

    def handle_glitch_single(self) -> None:
        """Trigger single glitch"""
        if not isinstance(self.backend, GlitchBackend):
            self.log("Device does not support glitching")
            return

        try:
            width_input = self.query_one("#glitch-width", Input)
            offset_input = self.query_one("#glitch-offset", Input)

            from ..backends import GlitchConfig

            cfg = GlitchConfig(
                width_ns=float(width_input.value),
                offset_ns=float(offset_input.value),
                repeat=1
            )

            self.backend.configure_glitch(cfg)
            self.backend.trigger()
            self.log(f"✓ Glitch sent: {cfg.width_ns:.0f}ns")
        except Exception as e:
            self.log(f"Error: {e}")

    def handle_glitch_sweep(self) -> None:
        """Start parameter sweep"""
        self.log("Parameter sweep not yet fully implemented")
        # This would start an async task to sweep parameters


def run_tui():
    """Launch the TUI app"""
    app = HwhApp()
    app.run()


if __name__ == "__main__":
    run_tui()
