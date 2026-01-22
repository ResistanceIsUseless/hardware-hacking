"""
UART Monitor Panel

Generic UART monitoring panel with regex filtering and highlighting.
Used for monitoring target devices during attacks.

Features:
- UART monitoring with configurable baud/format
- Regex filters with color highlighting
- Pattern matching triggers
- Logging to file
"""

import asyncio
import re
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass, field

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Input, Select, Switch, Log
from textual.messages import Message

from .base import DevicePanel, DeviceInfo, PanelCapability, CommandSuggestion


@dataclass
class UartFilter:
    """UART output filter with regex pattern and color"""
    pattern: str
    color: str = "#00ff00"  # Green by default
    enabled: bool = True
    name: str = ""


class UARTDataMessage(Message):
    """Message for incoming UART data"""
    def __init__(self, data: str):
        super().__init__()
        self.data = data


class UARTMonitorPanel(DevicePanel):
    """
    Generic UART monitoring panel.

    Perfect for:
    - Monitoring target boot sequences
    - Watching for glitch success indicators
    - Capturing debug output
    - Logging serial communication
    """

    DEVICE_NAME = "UART Monitor"
    CAPABILITIES = [PanelCapability.UART]

    # Default filter colors
    FILTER_COLORS = [
        "#00ff00",  # Green
        "#ff0000",  # Red
        "#ffff00",  # Yellow
        "#00ffff",  # Cyan
        "#ff00ff",  # Magenta
        "#ff8800",  # Orange
    ]

    def __init__(self, device_info: DeviceInfo, app, *args, **kwargs):
        super().__init__(device_info, app, *args, **kwargs)

        # UART configuration
        self.baud_rate = 115200
        self.data_bits = 8
        self.parity = "N"
        self.stop_bits = 1

        # Filters
        self.filters: List[UartFilter] = []
        self._color_index = 0

        # Serial connection
        self._serial = None
        self._read_task: Optional[asyncio.Task] = None

        # Logging
        self.logging_enabled = False
        self.log_file: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="uart-monitor-panel"):
            # Header with connection settings
            with Horizontal(classes="panel-header"):
                yield Static(f"{self.device_info.name}", classes="device-title")
                yield Static(f"Port: {self.device_info.port}", classes="device-port")

            # Configuration row
            with Horizontal(classes="uart-config"):
                yield Static("Baud:")
                yield Select(
                    [("9600", "9600"), ("19200", "19200"), ("38400", "38400"),
                     ("57600", "57600"), ("115200", "115200"), ("230400", "230400"),
                     ("460800", "460800"), ("921600", "921600")],
                    value="115200",
                    id="uart-baud",
                    classes="uart-select"
                )
                yield Static("Format:")
                yield Select(
                    [("8N1", "8N1"), ("8E1", "8E1"), ("8O1", "8O1"),
                     ("7E1", "7E1"), ("7O1", "7O1")],
                    value="8N1",
                    id="uart-format",
                    classes="uart-select"
                )
                yield Button("Connect", id="btn-uart-connect", classes="btn-small")
                yield Button("Disconnect", id="btn-uart-disconnect", classes="btn-small")

            # Main content
            with Horizontal(classes="uart-main"):
                # UART output area
                with Vertical(classes="uart-output-section"):
                    uart_log = Log(id="uart-output", classes="uart-log")
                    uart_log.border_title = "output"
                    yield uart_log

                    # Input row
                    with Horizontal(classes="input-row"):
                        yield Static("$> ", classes="input-prompt")
                        yield Input(placeholder="send to uart...", id="uart-input")
                        yield Button("Send", id="btn-send", classes="btn-small")

                # Filter sidebar
                with Vertical(classes="filter-sidebar") as sidebar:
                    sidebar.border_title = "filters"

                    yield Static("Regex patterns to highlight:", classes="help-text")

                    # Active filters list
                    yield Container(id="filter-list", classes="filter-list")

                    # Add filter controls
                    with Horizontal(classes="add-filter-row"):
                        yield Input(placeholder="regex pattern...", id="filter-pattern")
                        yield Button("+", id="btn-add-filter", classes="btn-small")

                    # Logging controls
                    yield Static("Logging:", classes="section-label")
                    with Horizontal(classes="logging-row"):
                        yield Switch(id="logging-switch", animate=False)
                        yield Static("Off", id="logging-status")

                    # Control buttons
                    with Vertical(classes="filter-buttons"):
                        yield Button("Clear Output", id="btn-clear", classes="btn-wide")
                        yield Button("Export Log", id="btn-export", classes="btn-wide")

    async def connect(self) -> bool:
        """Connect to UART device"""
        try:
            import serial
            self._serial = serial.Serial(
                self.device_info.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                parity=self.parity,
                stopbits=self.stop_bits,
                timeout=0.1
            )

            self.connected = True
            self.log_output(f"[+] Connected to {self.device_info.port}")
            self.log_output(f"[*] Baud: {self.baud_rate}, Format: {self.data_bits}{self.parity}{self.stop_bits}")

            # Start reading task
            self._read_task = asyncio.create_task(self._read_serial())

            return True

        except ImportError:
            self.log_output("[!] pyserial not installed. Install with: pip install pyserial")
            self.connected = True  # Allow UI testing
            return True
        except Exception as e:
            self.log_output(f"[!] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from UART"""
        if self._read_task:
            self._read_task.cancel()
            self._read_task = None

        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

        self.connected = False
        self.log_output(f"[-] Disconnected from {self.device_info.port}")

    async def _read_serial(self) -> None:
        """Background task to read serial data"""
        buffer = ""

        while self.connected and self._serial:
            try:
                # Read available data
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._serial.read(self._serial.in_waiting or 1)
                )

                if data:
                    decoded = data.decode('utf-8', errors='ignore')

                    # Process characters
                    for char in decoded:
                        if char == '\r':
                            continue

                        buffer += char

                        if char == '\n':
                            self._process_line(buffer)
                            buffer = ""

                    # Flush partial line
                    if buffer and not buffer.endswith('\n'):
                        self._process_line(buffer)
                        buffer = ""

                await asyncio.sleep(0.01)

            except Exception as e:
                self.log_output(f"[!] Read error: {e}")
                break

    def _process_line(self, line: str) -> None:
        """Process a line of UART output"""
        # Write to log
        self._write_uart_output(line)

        # Check pattern callbacks
        for pattern, callback in self._pattern_callbacks.items():
            try:
                if re.search(pattern, line):
                    callback(line)
            except Exception:
                pass

        # Log to file if enabled
        if self.logging_enabled and self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    f.write(line)
            except Exception:
                pass

    def _write_uart_output(self, text: str) -> None:
        """Write text to UART output with filter highlighting"""
        display_text = text

        # Check filters for highlighting
        for f in self.filters:
            if not f.enabled:
                continue
            try:
                if re.search(f.pattern, text):
                    # Apply color markup (Rich markup)
                    display_text = f"[{f.color}]{text}[/]"
                    break
            except re.error:
                pass

        # Write to local log widget
        try:
            uart_log = self.query_one("#uart-output", Log)
            uart_log.write(display_text)
        except Exception:
            pass

        # Notify output callbacks (for mirrors and automation)
        for callback in self._output_callbacks:
            try:
                callback(text)
            except Exception:
                pass

    def add_filter(self, pattern: str, color: Optional[str] = None, name: str = "") -> bool:
        """Add a new filter"""
        # Validate pattern
        try:
            re.compile(pattern)
        except re.error as e:
            self.log_output(f"[!] Invalid regex: {e}")
            return False

        # Auto-assign color
        if color is None:
            color = self.FILTER_COLORS[self._color_index % len(self.FILTER_COLORS)]
            self._color_index += 1

        # Create filter
        uart_filter = UartFilter(
            pattern=pattern,
            color=color,
            name=name or pattern[:20]
        )
        self.filters.append(uart_filter)

        self.log_output(f"[+] Added filter: {pattern}")
        self._update_filter_list()
        return True

    def remove_filter(self, index: int) -> None:
        """Remove a filter by index"""
        if 0 <= index < len(self.filters):
            removed = self.filters.pop(index)
            self.log_output(f"[-] Removed filter: {removed.pattern}")
            self._update_filter_list()

    def _update_filter_list(self) -> None:
        """Update the filter list display"""
        # This would update the UI to show current filters
        pass

    async def send_command(self, command: str) -> None:
        """Handle commands"""
        await super().send_command(command)

        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "help":
            self._show_help()
        elif cmd == "filter":
            self._handle_filter_command(parts[1:])
        elif cmd == "clear":
            self._clear_output()
        elif cmd == "send":
            await self._send_uart(" ".join(parts[1:]))
        else:
            # Send as raw UART data
            await self._send_uart(command)

    async def _send_uart(self, data: str) -> None:
        """Send data to UART"""
        if self._serial and self._serial.is_open:
            try:
                self._serial.write((data + "\n").encode())
                self.log_output(f"> {data}")
            except Exception as e:
                self.log_output(f"[!] Send failed: {e}")
        else:
            self.log_output(f"[!] Not connected")

    def _handle_filter_command(self, args: List[str]) -> None:
        """Handle filter commands"""
        if not args:
            self.log_output("[!] Usage: filter add <pattern> | filter remove <index> | filter list")
            return

        subcmd = args[0].lower()
        if subcmd == "add" and len(args) > 1:
            self.add_filter(args[1])
        elif subcmd == "remove" and len(args) > 1:
            try:
                self.remove_filter(int(args[1]))
            except ValueError:
                self.log_output("[!] Invalid index")
        elif subcmd == "list":
            self.log_output("Active filters:")
            for i, f in enumerate(self.filters):
                status = "ON" if f.enabled else "OFF"
                self.log_output(f"  {i}: [{status}] {f.pattern}")

    def _clear_output(self) -> None:
        """Clear UART output"""
        try:
            uart_log = self.query_one("#uart-output", Log)
            uart_log.clear()
        except Exception:
            pass

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """Get suggestions"""
        suggestions = [
            CommandSuggestion("help", "Show available commands"),
            CommandSuggestion("filter add", "Add a regex filter", "filter"),
            CommandSuggestion("filter remove", "Remove a filter", "filter"),
            CommandSuggestion("filter list", "List active filters", "filter"),
            CommandSuggestion("clear", "Clear output"),
            CommandSuggestion("send", "Send data to UART"),
        ]

        if partial:
            partial_lower = partial.lower()
            suggestions = [s for s in suggestions if s.command.lower().startswith(partial_lower)]

        return suggestions

    def _show_help(self) -> None:
        """Display help"""
        help_text = """
UART Monitor Commands:
  help                    - Show this help
  filter add <pattern>    - Add regex filter
  filter remove <index>   - Remove filter by index
  filter list             - List active filters
  clear                   - Clear output window
  send <text>             - Send text to UART
  <text>                  - Send directly to UART

Filter Examples:
  filter add "Boot"       - Highlight lines with "Boot"
  filter add "Error.*"    - Highlight error messages
  filter add "Glitch"     - Watch for glitch success
"""
        self.log_output(help_text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "btn-uart-connect":
            await self.connect()
        elif button_id == "btn-uart-disconnect":
            await self.disconnect()
        elif button_id == "btn-add-filter":
            try:
                pattern_input = self.query_one("#filter-pattern", Input)
                if pattern_input.value:
                    self.add_filter(pattern_input.value)
                    pattern_input.value = ""
            except Exception:
                pass
        elif button_id == "btn-clear":
            self._clear_output()
        elif button_id == "btn-send":
            try:
                uart_input = self.query_one("#uart-input", Input)
                if uart_input.value:
                    await self._send_uart(uart_input.value)
                    uart_input.value = ""
            except Exception:
                pass

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes"""
        if event.switch.id == "logging-switch":
            self.logging_enabled = event.value
            try:
                status = self.query_one("#logging-status", Static)
                if event.value:
                    import time
                    self.log_file = f"uart_{int(time.time())}.log"
                    status.update(f"On ({self.log_file})")
                else:
                    status.update("Off")
                    self.log_file = None
            except Exception:
                pass
