"""
Universal TUI for hwh - Hardware Hacking Tool

Multi-device interface supporting simultaneous connections.
Design inspired by glitch-o-bolt by 0xRoM.
"""

import asyncio
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Switch, Input, Log, TabbedContent, TabPane, DataTable
from textual.messages import Message

from ..detect import detect, DeviceInfo
from ..backends import get_backend, Backend, BusBackend, DebugBackend, GlitchBackend


@dataclass
class UartFilter:
    """UART output filter with regex pattern and highlight color"""
    pattern: str
    color: str
    enabled: bool = True


class DeviceConnection:
    """Represents a connected device with its backend"""
    def __init__(self, device: DeviceInfo, backend: Backend):
        self.device = device
        self.backend = backend
        self.connected = False
        self.uart_buffer = ""


class DeviceMessage(Message):
    """Message sent when device selection changes"""
    def __init__(self, device_id: str):
        super().__init__()
        self.device_id = device_id


class SerialDataMessage(Message):
    """Message sent when serial data is received"""
    def __init__(self, device_id: str, data: str):
        super().__init__()
        self.device_id = device_id
        self.data = data


class HwhApp(App):
    """
    Multi-device hardware hacking TUI

    Supports connecting to multiple devices simultaneously:
    - Monitor UART on one device while glitching with another
    - Compare outputs from multiple targets
    - Coordinate multi-tool attacks
    """

    CSS_PATH = "style.tcss"
    TITLE = "hwh - Universal Hardware Hacking Tool"

    def __init__(self):
        super().__init__()
        self.available_devices: Dict[str, DeviceInfo] = {}
        self.connections: Dict[str, DeviceConnection] = {}
        self.selected_device: Optional[str] = None

        # Glitch parameters (when glitch device is selected)
        self.glitch_length = 0
        self.glitch_repeat = 0
        self.glitch_delay = 0
        self.glitch_running = False

        # UART filters
        self.uart_filters: List[UartFilter] = []

    async def on_ready(self) -> None:
        """Initialize: detect devices and prepare UI"""
        # Detect all available devices
        self.available_devices = detect()

        if not self.available_devices:
            self.notify("No devices detected!", severity="warning")
            return

        # Populate device list
        await self.refresh_device_list()

    async def refresh_device_list(self) -> None:
        """Update the device list display"""
        device_list = self.query_one("#device-list", Container)
        await device_list.remove_children()

        # Add device entries
        for device_id, device_info in self.available_devices.items():
            is_connected = device_id in self.connections
            status_symbol = "●" if is_connected else "○"
            status_class = "status-on" if is_connected else "status-off"

            # Create device entry with all widgets
            entry = Horizontal(classes="device-entry")

            # Mount entry to device_list first, then add children
            await device_list.mount(entry)

            # Now add children to the mounted entry
            await entry.mount(Static(status_symbol, classes=status_class))
            await entry.mount(Static(device_info.name))
            await entry.mount(Static(f"({device_info.vid:04x}:{device_info.pid:04x})"))

            if is_connected:
                await entry.mount(Button("Disconnect", id=f"disconnect-{device_id}", classes="btn-small"))
            else:
                await entry.mount(Button("Connect", id=f"connect-{device_id}", classes="btn-small"))

    def compose(self) -> ComposeResult:
        """Build the multi-device UI"""

        with Container(id="main-layout"):
            # Left sidebar - Device list and status
            with Vertical(id="sidebar"):
                with Container(id="device-section") as device_section:
                    device_section.border_title = "devices"

                    # Device list container (populated dynamically)
                    yield Container(id="device-list")

                # Glitch controls (shown when glitch device is selected)
                with Container(id="glitch-section", classes="hidden") as glitch_section:
                    glitch_section.border_title = "glitch parameters"

                    # Length control
                    with Horizontal(classes="param-row"):
                        yield Static("length:", classes="param-label")
                        for amount in [-100, -10, -1]:
                            yield Button(str(amount), classes="btn-adjust", id=f"length-neg-{abs(amount)}")
                        yield Input(value="0", id="length-input", classes="param-input")
                        yield Button("save", classes="btn-save", id="length-save")
                        for amount in [1, 10, 100]:
                            yield Button(f"+{amount}", classes="btn-adjust", id=f"length-pos-{amount}")

                    # Repeat control
                    with Horizontal(classes="param-row"):
                        yield Static("repeat:", classes="param-label")
                        for amount in [-100, -10, -1]:
                            yield Button(str(amount), classes="btn-adjust", id=f"repeat-neg-{abs(amount)}")
                        yield Input(value="0", id="repeat-input", classes="param-input")
                        yield Button("save", classes="btn-save", id="repeat-save")
                        for amount in [1, 10, 100]:
                            yield Button(f"+{amount}", classes="btn-adjust", id=f"repeat-pos-{amount}")

                    # Delay control
                    with Horizontal(classes="param-row"):
                        yield Static("delay:", classes="param-label")
                        for amount in [-100, -10, -1]:
                            yield Button(str(amount), classes="btn-adjust", id=f"delay-neg-{abs(amount)}")
                        yield Input(value="0", id="delay-input", classes="param-input")
                        yield Button("save", classes="btn-save", id="delay-save")
                        for amount in [1, 10, 100]:
                            yield Button(f"+{amount}", classes="btn-adjust", id=f"delay-pos-{amount}")

                    # Glitch control
                    with Vertical(classes="glitch-control"):
                        yield Button("glitch", classes="btn-glitch", id="btn-glitch")
                        yield Switch(id="glitch-switch", animate=False)

                    # Status box
                    status_table = DataTable(id="glitch-status", show_header=False, show_cursor=False)
                    status_table.border_title = "status"
                    status_table.add_columns("Param", "Value")
                    status_table.add_row("length:", "0", key="length")
                    status_table.add_row("repeat:", "0", key="repeat")
                    status_table.add_row("delay:", "0", key="delay")
                    status_table.add_row("elapsed:", "00:00:00", key="elapsed")
                    yield status_table

            # Main content area
            with Container(id="main-content"):
                with TabbedContent(id="tabs"):
                    # Console tab - shows all device output
                    with TabPane("Console", id="tab-console"):
                        self.console_log = Log(id="console-output")
                        yield self.console_log

                        with Horizontal(classes="input-row"):
                            yield Static("$> ")
                            yield Input(placeholder="command...", id="console-input")

                    # UART tab - multi-device monitoring with filters
                    with TabPane("UART", id="tab-uart"):
                        with Horizontal(id="uart-layout"):
                            # UART output area
                            with Vertical(classes="uart-output-section"):
                                self.uart_log = Log(id="uart-output")
                                yield self.uart_log

                                with Horizontal(classes="input-row"):
                                    yield Static("$> ")
                                    yield Input(placeholder="send to UART...", id="uart-input")

                            # Filter controls
                            with Vertical(id="uart-filters") as filter_section:
                                filter_section.border_title = "filters"

                                yield Static("Regex patterns to highlight:")

                                # Filter entries (add dynamically)
                                yield Container(id="filter-list")

                                with Horizontal():
                                    yield Input(placeholder="regex pattern...", id="filter-pattern")
                                    yield Button("Add", id="add-filter", classes="btn-small")

                    # SPI tab
                    with TabPane("SPI", id="tab-spi"):
                        yield from self._build_spi_controls()

                    # I2C tab
                    with TabPane("I2C", id="tab-i2c"):
                        yield from self._build_i2c_controls()

                    # Debug tab
                    with TabPane("Debug", id="tab-debug"):
                        yield from self._build_debug_controls()

    def _build_spi_controls(self) -> ComposeResult:
        """Build SPI controls"""
        with Vertical():
            yield Static("SPI Configuration")

            with Grid(classes="config-grid"):
                yield Static("Speed:")
                yield Input(value="1000000", id="spi-speed")

                yield Static("Mode:")
                yield Input(value="0", id="spi-mode")

            yield Button("Configure", id="btn-spi-config", classes="btn-wide")

            yield Static("Operations")
            yield Button("Read Flash ID", id="btn-spi-id", classes="btn-wide")
            yield Button("Dump Flash", id="btn-spi-dump", classes="btn-wide")

    def _build_i2c_controls(self) -> ComposeResult:
        """Build I2C controls"""
        with Vertical():
            yield Static("I2C Configuration")

            with Grid(classes="config-grid"):
                yield Static("Speed:")
                yield Input(value="100000", id="i2c-speed")

                yield Static("Address:")
                yield Input(value="0x50", id="i2c-addr")

            yield Button("Configure", id="btn-i2c-config", classes="btn-wide")

            yield Static("Operations")
            yield Button("Scan Bus", id="btn-i2c-scan", classes="btn-wide")
            yield Button("Read Byte", id="btn-i2c-read", classes="btn-wide")

    def _build_debug_controls(self) -> ComposeResult:
        """Build debug/SWD/JTAG controls"""
        with Vertical():
            yield Static("Debug Operations")

            yield Button("Connect Target", id="btn-debug-connect", classes="btn-wide")
            yield Button("Reset Target", id="btn-debug-reset", classes="btn-wide")
            yield Button("Halt", id="btn-debug-halt", classes="btn-wide")
            yield Button("Resume", id="btn-debug-resume", classes="btn-wide")

            yield Static("Memory")

            with Grid(classes="config-grid"):
                yield Static("Address:")
                yield Input(value="0x08000000", id="debug-addr")

                yield Static("Size:")
                yield Input(value="0x1000", id="debug-size")

            yield Button("Read Memory", id="btn-debug-read", classes="btn-wide")
            yield Button("Dump Firmware", id="btn-debug-dump", classes="btn-wide")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle all button presses"""
        button_id = event.button.id

        if not button_id:
            return

        # Device connection/disconnection
        if button_id.startswith("connect-"):
            device_id = button_id.replace("connect-", "")
            await self.connect_device(device_id)

        elif button_id.startswith("disconnect-"):
            device_id = button_id.replace("disconnect-", "")
            await self.disconnect_device(device_id)

        # Glitch parameter adjustments
        elif button_id.startswith(("length", "repeat", "delay")):
            await self.handle_param_adjust(button_id)

        # Glitch control
        elif button_id == "btn-glitch":
            await self.trigger_glitch()

        # UART filter
        elif button_id == "add-filter":
            await self.add_uart_filter()

        # Protocol operations
        elif button_id.startswith("btn-"):
            await self.handle_protocol_button(button_id)

    async def connect_device(self, device_id: str) -> None:
        """Connect to a device"""
        if device_id in self.connections:
            self.console_log.write_line(f"[!] {device_id} already connected")
            return

        device_info = self.available_devices.get(device_id)
        if not device_info:
            return

        try:
            # Create backend
            backend = get_backend(device_info)
            backend.connect()

            # Store connection
            conn = DeviceConnection(device_info, backend)
            conn.connected = True
            self.connections[device_id] = conn

            self.console_log.write_line(f"[+] Connected to {device_info.name}")

            # If this is a glitch device, show glitch controls
            if "glitch" in device_info.capabilities:
                glitch_section = self.query_one("#glitch-section")
                glitch_section.remove_class("hidden")
                self.selected_device = device_id

            # Refresh device list
            await self.refresh_device_list()

        except Exception as e:
            self.console_log.write_line(f"[!] Failed to connect to {device_info.name}: {e}")

    async def disconnect_device(self, device_id: str) -> None:
        """Disconnect from a device"""
        conn = self.connections.get(device_id)
        if not conn:
            return

        try:
            conn.backend.disconnect()
            del self.connections[device_id]

            self.console_log.write_line(f"[-] Disconnected from {conn.device.name}")

            # If this was the selected glitch device, hide glitch controls
            if device_id == self.selected_device:
                glitch_section = self.query_one("#glitch-section")
                glitch_section.add_class("hidden")
                self.selected_device = None

            # Refresh device list
            await self.refresh_device_list()

        except Exception as e:
            self.console_log.write_line(f"[!] Error disconnecting: {e}")

    async def handle_param_adjust(self, button_id: str) -> None:
        """Handle glitch parameter increment/decrement buttons"""
        # Parse button ID: "length-neg-100", "repeat-pos-10", etc.
        parts = button_id.split("-")
        if len(parts) != 3:
            return

        param_name = parts[0]  # "length", "repeat", or "delay"
        direction = parts[1]   # "pos" or "neg"
        amount = int(parts[2]) # 1, 10, 100

        # Calculate adjustment
        adjustment = amount if direction == "pos" else -amount

        # Get current value
        input_widget = self.query_one(f"#{param_name}-input", Input)
        current_value = int(input_widget.value or "0")

        # Apply adjustment
        new_value = max(0, current_value + adjustment)  # Don't go negative
        input_widget.value = str(new_value)

        # Update stored value
        if param_name == "length":
            self.glitch_length = new_value
        elif param_name == "repeat":
            self.glitch_repeat = new_value
        elif param_name == "delay":
            self.glitch_delay = new_value

        # Update status table
        status_table = self.query_one("#glitch-status", DataTable)
        status_table.update_cell(param_name, "Value", str(new_value))

    async def trigger_glitch(self) -> None:
        """Trigger a single glitch or start continuous glitching"""
        if not self.selected_device:
            self.console_log.write_line("[!] No glitch device selected")
            return

        conn = self.connections.get(self.selected_device)
        if not conn or not isinstance(conn.backend, GlitchBackend):
            self.console_log.write_line("[!] Selected device does not support glitching")
            return

        try:
            from ..backends import GlitchConfig

            cfg = GlitchConfig(
                width_ns=float(self.glitch_length),
                offset_ns=float(self.glitch_delay),
                repeat=self.glitch_repeat
            )

            conn.backend.configure_glitch(cfg)
            conn.backend.trigger()

            self.console_log.write_line(f"[*] Glitch: {self.glitch_length}ns @ {self.glitch_delay}ns, repeat={self.glitch_repeat}")

        except Exception as e:
            self.console_log.write_line(f"[!] Glitch failed: {e}")

    async def add_uart_filter(self) -> None:
        """Add a new UART regex filter"""
        pattern_input = self.query_one("#filter-pattern", Input)
        pattern = pattern_input.value.strip()

        if not pattern:
            return

        # Validate regex
        try:
            re.compile(pattern)
        except re.error as e:
            self.console_log.write_line(f"[!] Invalid regex: {e}")
            return

        # Add filter
        uart_filter = UartFilter(pattern=pattern, color="#00ff00")
        self.uart_filters.append(uart_filter)

        self.console_log.write_line(f"[+] Added UART filter: {pattern}")
        pattern_input.value = ""

        # TODO: Update filter list display

    async def handle_protocol_button(self, button_id: str) -> None:
        """Handle SPI/I2C/Debug button presses"""
        self.console_log.write_line(f"[*] {button_id} - not yet implemented")

        # Implementation will depend on which device is selected and what protocol

    async def on_serial_data_message(self, message: SerialDataMessage) -> None:
        """Handle incoming serial data from any device"""
        # Write to console
        self.console_log.write(f"[{message.device_id}] {message.data}")

        # Write to UART tab with filtering
        uart_output = message.data

        # Apply filters
        for uart_filter in self.uart_filters:
            if not uart_filter.enabled:
                continue

            try:
                if re.search(uart_filter.pattern, uart_output):
                    # Highlight matching text
                    # TODO: Apply color highlighting
                    pass
            except re.error:
                pass

        self.uart_log.write(f"[{message.device_id}] {uart_output}")


def run_tui():
    """Launch the TUI"""
    app = HwhApp()
    app.run()


if __name__ == "__main__":
    run_tui()
