"""
Base Device Panel

Abstract base class for all device panels in the TUI.
Each panel represents a connected device and provides UI for its capabilities.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Log, Input
from textual.messages import Message

if TYPE_CHECKING:
    from ..app import HwhApp


class PanelCapability(Enum):
    """Capabilities that a device panel can provide"""
    UART = auto()           # Serial communication
    SPI = auto()            # SPI protocol
    I2C = auto()            # I2C protocol
    JTAG = auto()           # JTAG debugging
    SWD = auto()            # SWD debugging
    GLITCH = auto()         # Voltage glitching
    EMFI = auto()           # Electromagnetic fault injection
    LOGIC = auto()          # Logic analyzer
    POWER = auto()          # Power analysis
    ADC = auto()            # Voltage measurement
    PWM = auto()            # PWM generation
    GPIO = auto()           # General purpose I/O
    FLASH = auto()          # Flash programming
    DEBUG = auto()          # Debug interface (GDB, etc)


@dataclass
class CommandSuggestion:
    """A command suggestion for auto-completion"""
    command: str
    description: str
    category: str = ""


@dataclass
class DeviceInfo:
    """Information about a connected device"""
    name: str
    port: str
    vid: int
    pid: int
    serial: str = ""
    capabilities: List[PanelCapability] = field(default_factory=list)


class DeviceStatusMessage(Message):
    """Message sent when device status changes"""
    def __init__(self, device_id: str, status: str, data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.device_id = device_id
        self.status = status
        self.data = data or {}


class DeviceOutputMessage(Message):
    """Message sent when device produces output"""
    def __init__(self, device_id: str, output: str, channel: str = "console"):
        super().__init__()
        self.device_id = device_id
        self.output = output
        self.channel = channel  # "console", "uart", "logic", etc.


class DevicePanel(Container):
    """
    Base class for device panels.

    Each device type (Bus Pirate, Bolt, etc.) implements this class
    to provide a custom UI for its capabilities.

    Device panels are created when a device is connected and destroyed
    when disconnected. They appear as tabs in the main TUI.

    Subclasses should override:
    - compose() - Build the panel UI
    - connect() - Connect to the device
    - disconnect() - Disconnect from the device
    """

    # Class attributes to be overridden by subclasses
    DEVICE_NAME: str = "Unknown Device"
    CAPABILITIES: List[PanelCapability] = []

    def __init__(
        self,
        device_info: DeviceInfo,
        app: "HwhApp",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.device_info = device_info
        self.hwh_app = app
        self.connected = False
        self._command_history: List[str] = []
        self._history_index = 0

        # Callbacks for automation
        self._output_callbacks: List[Callable[[str], None]] = []
        self._pattern_callbacks: Dict[str, Callable[[str], None]] = {}

    @property
    def device_id(self) -> str:
        """Unique identifier for this device"""
        return f"{self.device_info.vid:04x}:{self.device_info.pid:04x}:{self.device_info.port}"

    @property
    def safe_id(self) -> str:
        """Sanitized identifier safe for use in Textual widget IDs.

        Textual IDs must contain only letters, numbers, underscores, or hyphens,
        and must not begin with a number.
        """
        import re
        # Replace colons, slashes, dots with underscores
        safe = re.sub(r'[:/.]', '_', self.device_id)
        # Remove any remaining invalid characters
        safe = re.sub(r'[^a-zA-Z0-9_-]', '', safe)
        # Ensure it doesn't start with a number
        if safe and safe[0].isdigit():
            safe = 'dev_' + safe
        return safe

    @property
    def tab_title(self) -> str:
        """Title to display in the tab"""
        return self.device_info.name

    def compose(self) -> ComposeResult:
        """Build the panel UI - override in subclasses"""
        yield Static(f"Panel for {self.device_info.name}")

    async def connect(self) -> bool:
        """
        Connect to the device.
        Returns True if successful, False otherwise.
        Override in subclasses.
        """
        return False

    async def disconnect(self) -> None:
        """Disconnect from the device. Override in subclasses."""
        pass

    async def send_command(self, command: str) -> None:
        """
        Send a command to the device.
        Override in subclasses for device-specific handling.
        """
        self._command_history.append(command)
        self._history_index = len(self._command_history)
        self.log_output(f"$ {command}")

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """
        Get command suggestions for auto-completion.
        Override in subclasses to provide device-specific suggestions.
        """
        return []

    def log_output(self, text: str, channel: str = "console") -> None:
        """
        Log output to the console and notify callbacks.

        Args:
            text: The text to log
            channel: The output channel (console, uart, etc.)
        """
        # Post message for TUI to handle
        self.post_message(DeviceOutputMessage(self.device_id, text, channel))

        # Notify callbacks
        for callback in self._output_callbacks:
            try:
                callback(text)
            except Exception:
                pass

        # Check pattern callbacks
        import re
        for pattern, callback in self._pattern_callbacks.items():
            try:
                if re.search(pattern, text):
                    callback(text)
            except Exception:
                pass

    def on_output(self, callback: Callable[[str], None]) -> None:
        """Register a callback to be called when output is received"""
        self._output_callbacks.append(callback)

    def on_pattern(self, pattern: str, callback: Callable[[str], None]) -> None:
        """Register a callback to be called when a regex pattern matches"""
        self._pattern_callbacks[pattern] = callback

    def get_previous_command(self) -> Optional[str]:
        """Get the previous command from history"""
        if self._history_index > 0:
            self._history_index -= 1
            return self._command_history[self._history_index]
        return None

    def get_next_command(self) -> Optional[str]:
        """Get the next command from history"""
        if self._history_index < len(self._command_history) - 1:
            self._history_index += 1
            return self._command_history[self._history_index]
        elif self._history_index == len(self._command_history) - 1:
            self._history_index = len(self._command_history)
            return ""
        return None

    def _build_console_section(self) -> ComposeResult:
        """Helper to build a standard console section"""
        with Container(classes="console-section") as console:
            console.border_title = "console"
            yield Log(id=f"console-{self.safe_id}", classes="device-console")
            with Horizontal(classes="input-row"):
                yield Static("$> ")
                yield Input(placeholder="command...", id=f"input-{self.safe_id}")

    def _build_status_section(self, items: Dict[str, str]) -> ComposeResult:
        """Helper to build a status display section"""
        from textual.widgets import DataTable

        table = DataTable(
            id=f"status-{self.safe_id}",
            show_header=False,
            show_cursor=False,
            classes="status-table"
        )
        table.add_columns("Param", "Value")
        for key, value in items.items():
            table.add_row(f"{key}:", value, key=key)
        yield table

    def update_status(self, key: str, value: str) -> None:
        """Update a value in the status table"""
        from textual.widgets import DataTable
        try:
            table = self.query_one(f"#status-{self.safe_id}", DataTable)
            table.update_cell(key, "Value", value)
        except Exception:
            pass

    def post_status(self, status: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Post a status update message"""
        self.post_message(DeviceStatusMessage(self.device_id, status, data))


class GenericPanel(DevicePanel):
    """
    A generic panel for unknown devices.
    Provides basic UART communication.
    """

    DEVICE_NAME = "Unknown Device"
    CAPABILITIES = [PanelCapability.UART]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(f"Generic device: {self.device_info.name}")
            yield Static(f"Port: {self.device_info.port}")
            yield Static(f"VID:PID: {self.device_info.vid:04x}:{self.device_info.pid:04x}")

            yield from self._build_console_section()

    async def connect(self) -> bool:
        self.connected = True
        self.log_output(f"Connected to {self.device_info.name}")
        return True

    async def disconnect(self) -> None:
        self.connected = False
        self.log_output(f"Disconnected from {self.device_info.name}")
