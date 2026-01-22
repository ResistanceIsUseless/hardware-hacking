"""
Curious Bolt Panel

Glitching panel for Curious Bolt / Curious Supplies devices.
UI design inspired by glitch-o-bolt by 0xRoM.

Features:
- Voltage glitching (8.3ns resolution)
- 8 trigger channels with edge detection
- Power analysis (35MSPS ADC)
- Logic analyzer (8 channels)
- Conditions monitoring for automated glitching
- UART passthrough to target
"""

import asyncio
import time
import re
import os
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Input, Switch, Log, DataTable, Select, ProgressBar
from textual.messages import Message
from textual.reactive import reactive

from .base import DevicePanel, PanelCapability, CommandSuggestion
from ...detect import DeviceInfo
from ...glitch_profiles import (
    GLITCH_PROFILES, GlitchProfile, find_profiles_for_chip,
    list_all_profiles, search_profiles
)


class TriggerEdge(Enum):
    RISING = "^"
    FALLING = "v"
    DISABLED = "-"


@dataclass
class GlitchConfig:
    """Glitch configuration parameters"""
    length: int = 0      # Glitch width in cycles (8.3ns per cycle)
    repeat: int = 1      # Number of manual trigger repeats
    delay: int = 0       # Delay before glitch in cycles (ext_offset)


@dataclass
class TriggerConfig:
    """Trigger channel configuration"""
    channel: int
    edge: TriggerEdge = TriggerEdge.DISABLED
    enabled: bool = False


@dataclass
class Condition:
    """Condition for automated responses"""
    name: str              # Display name
    enabled: bool = False  # Whether condition is active
    pattern: str = ""      # Regex pattern to match
    action: str = ""       # Action to execute when pattern matches


class SerialDataMessage(Message):
    """Message sent when serial data is received from target"""
    def __init__(self, data: str):
        super().__init__()
        self.data = data


class GlitchStatusMessage(Message):
    """Message sent when glitch status changes"""
    def __init__(self, running: bool, elapsed: float = 0.0):
        super().__init__()
        self.running = running
        self.elapsed = elapsed


class CircularDial(Static):
    """A circular dial widget for parameter adjustment"""

    value = reactive(0)
    max_value = reactive(1000)
    label = reactive("")

    def __init__(
        self,
        label: str = "",
        value: int = 0,
        max_value: int = 1000,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.label = label
        self.value = value
        self.max_value = max_value

    def render(self) -> str:
        """Render the dial as a visual circular indicator"""
        # Calculate fill percentage
        pct = min(100, (self.value / max(1, self.max_value)) * 100)

        # Create a simple arc representation
        # Using unicode block characters for a gauge effect
        filled = int(pct / 10)
        empty = 10 - filled

        bar = "█" * filled + "░" * empty

        return f"[{bar}] {self.value}"


class BoltPanel(DevicePanel):
    """
    Panel for Curious Bolt / Curious Supplies glitching devices.

    UI inspired by glitch-o-bolt:
    - Parameter controls with +/- buttons and circular dials
    - 8 trigger channels with edge toggles
    - Status box showing current settings
    - Conditions monitoring for automated actions
    - UART passthrough to target device
    """

    DEVICE_NAME = "Curious Bolt"
    CAPABILITIES = [
        PanelCapability.GLITCH,
        PanelCapability.LOGIC,
        PanelCapability.POWER,
        PanelCapability.GPIO,
    ]

    # Bolt timing constant
    CLOCK_PERIOD_NS = 8.3  # Single clock cycle duration

    def __init__(self, device_info: DeviceInfo, app, *args, **kwargs):
        super().__init__(device_info, app, *args, **kwargs)

        # Glitch parameters
        self.glitch_config = GlitchConfig()
        self.glitch_running = False
        self.glitch_start_time: Optional[float] = None
        self._glitch_task: Optional[asyncio.Task] = None
        self._glitch_count = 0

        # Triggers (8 channels)
        self.triggers: List[TriggerConfig] = [
            TriggerConfig(channel=i) for i in range(8)
        ]

        # Conditions for automated monitoring
        self.conditions: List[Condition] = [
            Condition(name="cond0", enabled=False, pattern="", action=""),
            Condition(name="cond1", enabled=False, pattern="", action=""),
            Condition(name="cond2", enabled=False, pattern="", action=""),
            Condition(name="cond3", enabled=False, pattern="", action=""),
        ]

        # Backend connection
        self._scope = None
        self._target_serial = None  # Serial connection to target via UART
        self._serial_buffer = ""
        self._buffer_lock = asyncio.Lock()

        # UART settings
        self.uart_enabled = False
        self.uart_output_enabled = False
        self.uart_port: Optional[str] = None
        self.uart_baud: int = 115200

        # Logging
        self.logging_enabled = False
        self.log_start_time: Optional[int] = None
        self._log_dir = Path("logs")

        # Glitch profiles
        self.current_profile: Optional[GlitchProfile] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="bolt-panel"):
            # Top section - glitch controls
            with Horizontal(classes="bolt-top-section"):
                # Left side - parameter dials
                with Vertical(classes="bolt-controls"):
                    # Length dial row
                    with Horizontal(classes="dial-row"):
                        yield Static("length", classes="dial-label")
                        yield Button("-100", classes="btn-dial btn-neg", id="length-sub-100")
                        yield Button("-10", classes="btn-dial btn-neg", id="length-sub-10")
                        yield Button("-1", classes="btn-dial btn-neg", id="length-sub-1")
                        yield CircularDial(
                            label="length",
                            value=self.glitch_config.length,
                            max_value=500,
                            id="dial-length",
                            classes="param-dial"
                        )
                        yield Button("+1", classes="btn-dial btn-pos", id="length-add-1")
                        yield Button("+10", classes="btn-dial btn-pos", id="length-add-10")
                        yield Button("+100", classes="btn-dial btn-pos", id="length-add-100")

                    # Repeat dial row
                    with Horizontal(classes="dial-row"):
                        yield Static("repeat", classes="dial-label")
                        yield Button("-100", classes="btn-dial btn-neg", id="repeat-sub-100")
                        yield Button("-10", classes="btn-dial btn-neg", id="repeat-sub-10")
                        yield Button("-1", classes="btn-dial btn-neg", id="repeat-sub-1")
                        yield CircularDial(
                            label="repeat",
                            value=self.glitch_config.repeat,
                            max_value=1000,
                            id="dial-repeat",
                            classes="param-dial"
                        )
                        yield Button("+1", classes="btn-dial btn-pos", id="repeat-add-1")
                        yield Button("+10", classes="btn-dial btn-pos", id="repeat-add-10")
                        yield Button("+100", classes="btn-dial btn-pos", id="repeat-add-100")

                    # Delay dial row
                    with Horizontal(classes="dial-row"):
                        yield Static("delay", classes="dial-label")
                        yield Button("-100", classes="btn-dial btn-neg", id="delay-sub-100")
                        yield Button("-10", classes="btn-dial btn-neg", id="delay-sub-10")
                        yield Button("-1", classes="btn-dial btn-neg", id="delay-sub-1")
                        yield CircularDial(
                            label="delay",
                            value=self.glitch_config.delay,
                            max_value=500,
                            id="dial-delay",
                            classes="param-dial"
                        )
                        yield Button("+1", classes="btn-dial btn-pos", id="delay-add-1")
                        yield Button("+10", classes="btn-dial btn-pos", id="delay-add-10")
                        yield Button("+100", classes="btn-dial btn-pos", id="delay-add-100")

                # Right side - glitch toggle and status
                with Vertical(classes="bolt-right-section"):
                    # Main glitch toggle (continuous mode)
                    with Vertical(classes="glitch-toggle-container"):
                        yield Static("GLITCH", classes="glitch-toggle-label")
                        yield Switch(id="glitch-toggle", animate=False, classes="glitch-main-switch")
                        yield Static("off", id="glitch-state-label", classes="glitch-state")

                    # Status display
                    with Vertical(classes="status-container") as status:
                        status.border_title = "status"
                        yield Static("length:  0", id="status-length", classes="status-line")
                        yield Static("repeat:  1", id="status-repeat", classes="status-line")
                        yield Static(" delay:  0", id="status-delay", classes="status-line")
                        yield Static("", classes="status-spacer")
                        yield Static("glitch: 0", id="status-count", classes="status-line")
                        yield Static("time: 00:00:00", id="status-time", classes="status-line")

            # Main section with sidebar and content
            with Horizontal(classes="bolt-main-section"):
                # Left sidebar - triggers and settings
                with Vertical(classes="bolt-sidebar"):
                    # Triggers section
                    with Vertical(classes="triggers-section") as triggers:
                        triggers.border_title = "triggers"
                        with Grid(classes="triggers-grid"):
                            for i in range(8):
                                yield Static(f"{i}", classes="trigger-index")
                                yield Static(
                                    self.triggers[i].edge.value,
                                    id=f"trigger-symbol-{i}",
                                    classes="trigger-symbol"
                                )
                                yield Switch(
                                    classes="trigger-switch",
                                    value=self.triggers[i].enabled,
                                    animate=False,
                                    id=f"trigger-switch-{i}"
                                )
                                yield Button(
                                    "^v-",
                                    classes="btn-edge",
                                    id=f"toggle-trigger-{i}"
                                )

                    # Profiles section
                    with Vertical(classes="profiles-section") as profiles:
                        profiles.border_title = "profiles"
                        profile_options = [
                            (p.name, p.name) for p in list_all_profiles()
                        ]
                        yield Select(
                            profile_options,
                            id="profile-select",
                            classes="profile-select",
                            prompt="Select chip..."
                        )
                        with Horizontal(classes="profile-buttons"):
                            yield Button("Load", id="btn-load-profile", classes="btn-profile-action")
                            yield Button("Info", id="btn-profile-info", classes="btn-profile-action")
                            yield Button("Save", id="btn-save-profile", classes="btn-profile-action")

                    # Conditions section
                    with Vertical(classes="conditions-section") as conditions:
                        conditions.border_title = "conditions"
                        with Grid(classes="conditions-grid"):
                            for i, cond in enumerate(self.conditions):
                                yield Static(f"c{i}", classes="condition-index")
                                yield Switch(
                                    id=f"condition-switch-{i}",
                                    classes="condition-switch",
                                    value=cond.enabled,
                                    animate=False
                                )
                                yield Button(
                                    "run",
                                    classes="btn-run-cond",
                                    id=f"run-condition-{i}"
                                )

                    # UART section
                    with Vertical(classes="uart-section") as uart:
                        uart.border_title = "target uart"
                        yield Input(
                            placeholder="/dev/ttyUSB0",
                            id="uart-port-input",
                            classes="uart-input"
                        )
                        with Horizontal(classes="uart-baud-row"):
                            yield Static("baud:", classes="uart-baud-label")
                            yield Input(
                                value="115200",
                                id="uart-baud-input",
                                classes="uart-baud-input"
                            )
                        yield Button("Connect", id="btn-uart-connect", classes="btn-uart")
                        with Horizontal(classes="uart-options-row"):
                            yield Static("output", classes="uart-opt-label")
                            yield Switch(id="uart-output", animate=False)
                            yield Static("log", classes="uart-opt-label")
                            yield Switch(id="logging-enable", animate=False)

                # Main content area - output log
                with Vertical(classes="bolt-content") as content:
                    content.border_title = "output"
                    yield Log(id="bolt-output", classes="bolt-log")

                    with Horizontal(classes="output-controls"):
                        yield Button("clear", id="clear-output", classes="btn-output-ctrl")
                        yield Button("export", id="export-log", classes="btn-output-ctrl")

                    with Horizontal(classes="input-row"):
                        yield Static("$>", classes="input-prompt")
                        yield Input(
                            placeholder="command or uart...",
                            id="bolt-input",
                            classes="bolt-input-field"
                        )

    async def connect(self) -> bool:
        """Connect to the Bolt device using the scope library"""
        try:
            # Try to import the native Bolt scope library
            try:
                # First try local tooling path
                import sys
                tooling_path = Path(__file__).parent.parent.parent / "tooling" / "glitch-o-bolt"
                if tooling_path.exists():
                    sys.path.insert(0, str(tooling_path))

                from scope import Scope
                self._scope = Scope()
                self.connected = True
                self._log_output(f"[+] Connected to {self.device_info.name}")
                self._log_output(f"[*] Scope library loaded successfully")

                # Initialize with safe defaults
                self._scope.glitch.repeat = self.glitch_config.length
                self._scope.glitch.ext_offset = self.glitch_config.delay

                self._sync_status()
                return True

            except ImportError as e:
                self._log_output(f"[!] Scope library not found: {e}")
                self._log_output("[*] Running in simulation mode")
                self.connected = True  # Allow UI testing
                return True

            except IOError as e:
                self._log_output(f"[!] Bolt not connected: {e}")
                self._log_output("[*] Running in simulation mode")
                self.connected = True  # Allow UI testing
                return True

        except Exception as e:
            self._log_output(f"[!] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Bolt"""
        # Stop continuous glitching
        if self._glitch_task:
            self._glitch_task.cancel()
            self._glitch_task = None

        # Disconnect scope
        if self._scope:
            try:
                self._scope.dis()
            except Exception:
                pass
            self._scope = None

        # Close target serial
        if self._target_serial:
            try:
                self._target_serial.close()
            except Exception:
                pass
            self._target_serial = None

        self.connected = False
        self._log_output(f"[-] Disconnected from {self.device_info.name}")

    def _log_output(self, text: str) -> None:
        """Write to the output log"""
        try:
            log = self.query_one("#bolt-output", Log)
            log.write_line(text)

            # Also write to file if logging enabled
            if self.logging_enabled and self.log_start_time:
                self._write_to_log_file(text + "\n")
        except Exception:
            pass

    def _write_to_log_file(self, text: str) -> None:
        """Write text to log file"""
        if not self.log_start_time:
            return

        try:
            self._log_dir.mkdir(exist_ok=True)
            log_file = self._log_dir / f"{self.log_start_time}.log"
            with open(log_file, "a") as f:
                f.write(text)
        except Exception:
            pass

    async def send_command(self, command: str) -> None:
        """Send command to Bolt"""
        await super().send_command(command)

        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "help":
            self._show_help()
        elif cmd == "glitch":
            await self._trigger_glitch()
        elif cmd == "set":
            await self._handle_set_command(parts[1:])
        elif cmd == "trigger":
            await self._handle_trigger_command(parts[1:])
        elif cmd == "status":
            self._show_status()
        elif cmd == "arm":
            self._arm_triggers()
        else:
            # Send to target UART if enabled
            if self.uart_enabled and self._target_serial:
                await self._send_to_target(command)
            else:
                self._log_output(f"Unknown command: {cmd}")

    async def _send_to_target(self, text: str) -> None:
        """Send text to target via UART"""
        if not self._target_serial or not self._target_serial.is_open:
            self._log_output("[!] UART not connected")
            return

        try:
            data = (text + "\r\n").encode("utf-8")
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._target_serial.write(data)
            )
            self._log_output(f"> {text}")
        except Exception as e:
            self._log_output(f"[!] UART TX error: {e}")

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """Get command suggestions"""
        suggestions = [
            CommandSuggestion("help", "Show available commands"),
            CommandSuggestion("glitch", "Trigger a glitch"),
            CommandSuggestion("set length", "Set glitch length in cycles", "set"),
            CommandSuggestion("set repeat", "Set manual trigger repeat count", "set"),
            CommandSuggestion("set delay", "Set glitch delay (ext_offset)", "set"),
            CommandSuggestion("trigger 0 rising", "Set trigger 0 to rising edge", "trigger"),
            CommandSuggestion("trigger 0 falling", "Set trigger 0 to falling edge", "trigger"),
            CommandSuggestion("arm", "Arm enabled triggers"),
            CommandSuggestion("status", "Show current status"),
        ]

        if partial:
            partial_lower = partial.lower()
            suggestions = [s for s in suggestions if s.command.lower().startswith(partial_lower)]

        return suggestions

    def _show_help(self) -> None:
        """Display help"""
        help_text = """
Commands:
  help                    - Show this help
  glitch                  - Trigger a single glitch
  set length <cycles>     - Set glitch width (8.3ns each)
  set repeat <count>      - Set trigger repeat count
  set delay <cycles>      - Set delay before glitch
  trigger <ch> <edge>     - Set trigger (rising/falling/off)
  arm                     - Arm enabled triggers
  status                  - Show current config

Toggle the main GLITCH switch for continuous mode.
"""
        self._log_output(help_text)

    def _show_status(self) -> None:
        """Display current status"""
        status = f"""
Configuration:
  Length: {self.glitch_config.length} ({self.glitch_config.length * self.CLOCK_PERIOD_NS:.1f}ns)
  Repeat: {self.glitch_config.repeat}
  Delay:  {self.glitch_config.delay} ({self.glitch_config.delay * self.CLOCK_PERIOD_NS:.1f}ns)

Triggers:
"""
        for t in self.triggers:
            status += f"  CH{t.channel}: {t.edge.value} {'[on]' if t.enabled else '[off]'}\n"

        status += f"""
UART: {'connected' if self.uart_enabled else 'disconnected'}
Mode: {'continuous' if self.glitch_running else 'manual'}
"""
        self._log_output(status)

    def _arm_triggers(self) -> None:
        """Arm all enabled triggers on the Bolt"""
        if not self._scope:
            self._log_output("[!] Scope not connected")
            return

        triggers_armed = False
        for t in self.triggers:
            if t.enabled and t.edge != TriggerEdge.DISABLED:
                try:
                    if t.edge == TriggerEdge.RISING:
                        self._scope.arm(t.channel, self._scope.RISING_EDGE)
                        self._log_output(f"[+] Armed trigger {t.channel} rising")
                    elif t.edge == TriggerEdge.FALLING:
                        self._scope.arm(t.channel, self._scope.FALLING_EDGE)
                        self._log_output(f"[+] Armed trigger {t.channel} falling")
                    triggers_armed = True
                except Exception as e:
                    self._log_output(f"[!] Failed to arm trigger {t.channel}: {e}")

        if not triggers_armed:
            self._log_output("[*] No triggers enabled")

    async def _trigger_glitch(self) -> None:
        """Trigger a single glitch"""
        # Configure glitch parameters
        if self._scope:
            try:
                self._scope.glitch.repeat = self.glitch_config.length
                self._scope.glitch.ext_offset = self.glitch_config.delay
            except Exception as e:
                self._log_output(f"[!] Config failed: {e}")
                return

        # Check if any triggers are enabled
        triggers_enabled = any(t.enabled and t.edge != TriggerEdge.DISABLED for t in self.triggers)

        if triggers_enabled:
            self._arm_triggers()
            self._log_output(f"[*] Armed - len={self.glitch_config.length}, dly={self.glitch_config.delay}")
        else:
            # Manual trigger
            if self._scope:
                try:
                    for _ in range(max(1, self.glitch_config.repeat)):
                        self._scope.trigger()
                    self._glitch_count += 1
                    self._update_glitch_count()
                    self._log_output(f"[+] Glitch #{self._glitch_count}")
                except Exception as e:
                    self._log_output(f"[!] Glitch failed: {e}")
            else:
                self._glitch_count += 1
                self._update_glitch_count()
                self._log_output(f"[*] Glitch #{self._glitch_count} (simulated)")

    async def _start_continuous_glitch(self) -> None:
        """Start continuous glitching"""
        self.glitch_running = True
        self.glitch_start_time = time.time()
        self._glitch_count = 0

        # Update UI state
        self._update_glitch_state(True)
        self._log_output("[*] Continuous glitching started")

        while self.glitch_running:
            try:
                # Configure and trigger
                if self._scope:
                    self._scope.glitch.repeat = self.glitch_config.length
                    self._scope.glitch.ext_offset = self.glitch_config.delay

                    triggers_enabled = any(t.enabled and t.edge != TriggerEdge.DISABLED for t in self.triggers)

                    if triggers_enabled:
                        self._arm_triggers()
                    else:
                        for _ in range(max(1, self.glitch_config.repeat)):
                            self._scope.trigger()
                        self._glitch_count += 1

                else:
                    # Simulation mode
                    self._glitch_count += 1

                # Update status
                self._update_glitch_count()
                self._update_elapsed_time()

                await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log_output(f"[!] Error: {e}")
                await asyncio.sleep(0.5)

    def _stop_continuous_glitch(self) -> None:
        """Stop continuous glitching"""
        self.glitch_running = False

        # Update UI state
        self._update_glitch_state(False)

        if self.glitch_start_time:
            elapsed = time.time() - self.glitch_start_time
            self._log_output(f"[*] Stopped - {self._glitch_count} glitches in {elapsed:.1f}s")

        self.glitch_start_time = None

    def _update_glitch_state(self, running: bool) -> None:
        """Update the glitch state label"""
        try:
            label = self.query_one("#glitch-state-label", Static)
            label.update("ON" if running else "off")
            if running:
                label.add_class("glitch-active")
            else:
                label.remove_class("glitch-active")
        except Exception:
            pass

    def _update_glitch_count(self) -> None:
        """Update the glitch count display"""
        try:
            count_label = self.query_one("#status-count", Static)
            count_label.update(f"glitch: {self._glitch_count}")
        except Exception:
            pass

    def _update_elapsed_time(self) -> None:
        """Update the elapsed time display"""
        if not self.glitch_start_time:
            return

        try:
            elapsed = time.time() - self.glitch_start_time
            h = int(elapsed) // 3600
            m = (int(elapsed) % 3600) // 60
            s = int(elapsed) % 60
            time_label = self.query_one("#status-time", Static)
            time_label.update(f"time: {h:02d}:{m:02d}:{s:02d}")
        except Exception:
            pass

    async def _handle_set_command(self, args: List[str]) -> None:
        """Handle set commands"""
        if len(args) < 2:
            self._log_output("[!] Usage: set <param> <value>")
            return

        param = args[0].lower()
        try:
            value = int(args[1])
        except ValueError:
            self._log_output(f"[!] Invalid value: {args[1]}")
            return

        if param == "length":
            self.glitch_config.length = max(0, value)
            self._update_param_display("length", self.glitch_config.length)
        elif param == "repeat":
            self.glitch_config.repeat = max(1, value)
            self._update_param_display("repeat", self.glitch_config.repeat)
        elif param == "delay":
            self.glitch_config.delay = max(0, value)
            self._update_param_display("delay", self.glitch_config.delay)
        else:
            self._log_output(f"[!] Unknown: {param}")
            return

        self._log_output(f"[+] {param} = {value}")

    async def _handle_trigger_command(self, args: List[str]) -> None:
        """Handle trigger commands"""
        if len(args) < 2:
            self._log_output("[!] Usage: trigger <ch> <rising|falling|off>")
            return

        try:
            channel = int(args[0])
            if not 0 <= channel < 8:
                raise ValueError("Channel must be 0-7")
        except ValueError as e:
            self._log_output(f"[!] {e}")
            return

        edge_str = args[1].lower()
        if edge_str in ("rising", "^"):
            edge = TriggerEdge.RISING
        elif edge_str in ("falling", "v"):
            edge = TriggerEdge.FALLING
        elif edge_str in ("off", "disabled", "-"):
            edge = TriggerEdge.DISABLED
        else:
            self._log_output(f"[!] Unknown edge: {edge_str}")
            return

        self.triggers[channel].edge = edge
        self._update_trigger_symbol(channel)
        self._log_output(f"[+] Trigger {channel} = {edge.name}")

    def _update_param_display(self, param: str, value: int) -> None:
        """Update parameter display (dial and status)"""
        try:
            # Update dial
            dial = self.query_one(f"#dial-{param}", CircularDial)
            dial.value = value

            # Update status
            if param == "length":
                label = self.query_one("#status-length", Static)
                label.update(f"length:  {value}")
            elif param == "repeat":
                label = self.query_one("#status-repeat", Static)
                label.update(f"repeat:  {value}")
            elif param == "delay":
                label = self.query_one("#status-delay", Static)
                label.update(f" delay:  {value}")
        except Exception:
            pass

    def _update_trigger_symbol(self, channel: int) -> None:
        """Update trigger symbol in UI"""
        try:
            symbol = self.query_one(f"#trigger-symbol-{channel}", Static)
            symbol.update(self.triggers[channel].edge.value)
        except Exception:
            pass

    def _sync_status(self) -> None:
        """Sync all status displays"""
        self._update_param_display("length", self.glitch_config.length)
        self._update_param_display("repeat", self.glitch_config.repeat)
        self._update_param_display("delay", self.glitch_config.delay)

    def _toggle_trigger_edge(self, channel: int) -> None:
        """Cycle through trigger edge modes"""
        current = self.triggers[channel].edge
        if current == TriggerEdge.DISABLED:
            new_edge = TriggerEdge.RISING
        elif current == TriggerEdge.RISING:
            new_edge = TriggerEdge.FALLING
        else:
            new_edge = TriggerEdge.DISABLED

        self.triggers[channel].edge = new_edge
        self._update_trigger_symbol(channel)
        self._log_output(f"[*] Trigger {channel}: {new_edge.value}")

    async def _handle_uart_connect(self) -> None:
        """Handle UART connect button press"""
        try:
            port_input = self.query_one("#uart-port-input", Input)
            baud_input = self.query_one("#uart-baud-input", Input)
            button = self.query_one("#btn-uart-connect", Button)

            port = port_input.value.strip()
            if not port:
                self._log_output("[!] Enter UART port")
                return

            try:
                baud = int(baud_input.value)
            except ValueError:
                baud = 115200

            # Toggle connection
            if self.uart_enabled and self._target_serial and self._target_serial.is_open:
                self._target_serial.close()
                self._target_serial = None
                self.uart_enabled = False
                button.label = "Connect"
                self._log_output(f"[-] UART disconnected")
            else:
                success = await self._connect_target_uart(port, baud)
                if success:
                    self.uart_enabled = True
                    button.label = "Disconnect"
                else:
                    self.uart_enabled = False

        except Exception as e:
            self._log_output(f"[!] UART error: {e}")

    async def _connect_target_uart(self, port: str, baud: int) -> bool:
        """Connect to target via UART"""
        try:
            import serial as pyserial

            if self._target_serial and self._target_serial.is_open:
                self._target_serial.close()

            self._target_serial = pyserial.Serial(
                port=port,
                baudrate=baud,
                timeout=0.1,
                write_timeout=1.0
            )

            self.uart_port = port
            self.uart_baud = baud
            self._log_output(f"[+] UART: {port} @ {baud}")

            asyncio.create_task(self._read_target_uart())
            return True

        except Exception as e:
            self._log_output(f"[!] UART failed: {e}")
            return False

    async def _read_target_uart(self) -> None:
        """Read data from target UART"""
        while self.uart_enabled and self._target_serial and self._target_serial.is_open:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._target_serial.read(
                        max(1, self._target_serial.in_waiting)
                    )
                )

                if data:
                    decoded = data.decode("utf-8", errors="ignore")

                    async with self._buffer_lock:
                        self._serial_buffer += decoded
                        if len(self._serial_buffer) > 4096:
                            self._serial_buffer = self._serial_buffer[-2048:]

                    if self.uart_output_enabled:
                        for char in decoded:
                            if char == '\r':
                                continue
                            self.post_message(SerialDataMessage(char))

                    await self._check_conditions()

                await asyncio.sleep(0.01)

            except Exception as e:
                self._log_output(f"[!] UART read error: {e}")
                break

    async def _check_conditions(self) -> None:
        """Check serial buffer against conditions"""
        async with self._buffer_lock:
            buffer = self._serial_buffer

        for i, cond in enumerate(self.conditions):
            if not cond.enabled or not cond.pattern:
                continue

            try:
                if re.search(cond.pattern, buffer):
                    self._log_output(f"[MATCH] {cond.name}")
                    await self._execute_condition_action(cond.action)

                    async with self._buffer_lock:
                        self._serial_buffer = ""
                    break

            except re.error:
                pass

    async def _execute_condition_action(self, action: str) -> None:
        """Execute a condition action"""
        if not action:
            return

        action = action.lower()

        if action == "glitch":
            await self._trigger_glitch()
        elif action == "stop":
            self._stop_continuous_glitch()
        elif action.startswith("set "):
            parts = action.split()
            if len(parts) >= 3:
                await self._handle_set_command(parts[1:])

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        if not button_id:
            return

        # Clear output
        if button_id == "clear-output":
            try:
                log = self.query_one("#bolt-output", Log)
                log.clear()
            except Exception:
                pass
            return

        # Export log
        if button_id == "export-log":
            self._export_current_log()
            return

        # UART connect
        if button_id == "btn-uart-connect":
            await self._handle_uart_connect()
            return

        # Profile buttons
        if button_id == "btn-load-profile":
            await self._load_selected_profile()
            return

        if button_id == "btn-profile-info":
            await self._show_profile_info()
            return

        if button_id == "btn-save-profile":
            await self._save_current_profile()
            return

        # Toggle trigger edge
        if button_id.startswith("toggle-trigger-"):
            try:
                channel = int(button_id.split("-")[-1])
                self._toggle_trigger_edge(channel)
            except ValueError:
                pass
            return

        # Run condition action
        if button_id.startswith("run-condition-"):
            try:
                index = int(button_id.split("-")[-1])
                if 0 <= index < len(self.conditions):
                    cond = self.conditions[index]
                    if cond.action:
                        await self._execute_condition_action(cond.action)
            except ValueError:
                pass
            return

        # Parameter dial buttons
        if "-sub-" in button_id or "-add-" in button_id:
            await self._handle_dial_button(button_id)
            return

    async def _handle_dial_button(self, button_id: str) -> None:
        """Handle dial adjustment buttons"""
        # Parse button_id: "length-sub-100" or "repeat-add-10"
        parts = button_id.split("-")
        if len(parts) != 3:
            return

        param = parts[0]
        direction = parts[1]
        amount = int(parts[2])

        adjustment = amount if direction == "add" else -amount

        if param == "length":
            self.glitch_config.length = max(0, self.glitch_config.length + adjustment)
            self._update_param_display("length", self.glitch_config.length)
        elif param == "repeat":
            self.glitch_config.repeat = max(1, self.glitch_config.repeat + adjustment)
            self._update_param_display("repeat", self.glitch_config.repeat)
        elif param == "delay":
            self.glitch_config.delay = max(0, self.glitch_config.delay + adjustment)
            self._update_param_display("delay", self.glitch_config.delay)

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch toggles"""
        switch_id = event.switch.id
        if not switch_id:
            return

        # Main glitch toggle (continuous mode)
        if switch_id == "glitch-toggle":
            if event.value:
                self._glitch_task = asyncio.create_task(self._start_continuous_glitch())
            else:
                self._stop_continuous_glitch()
                if self._glitch_task:
                    self._glitch_task.cancel()
                    self._glitch_task = None
            return

        # UART output display
        if switch_id == "uart-output":
            self.uart_output_enabled = event.value
            return

        # Logging
        if switch_id == "logging-enable":
            self.logging_enabled = event.value
            if event.value:
                self.log_start_time = int(time.time())
                self._log_output(f"[*] Logging: logs/{self.log_start_time}.log")
            else:
                self.log_start_time = None
            return

        # Trigger switches
        if switch_id.startswith("trigger-switch-"):
            try:
                channel = int(switch_id.split("-")[-1])
                self.triggers[channel].enabled = event.value
            except ValueError:
                pass
            return

        # Condition switches
        if switch_id.startswith("condition-switch-"):
            try:
                index = int(switch_id.split("-")[-1])
                if 0 <= index < len(self.conditions):
                    self.conditions[index].enabled = event.value
            except ValueError:
                pass
            return

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission"""
        if event.input.id == "bolt-input":
            command = event.value.strip()
            if command:
                event.input.value = ""
                await self.send_command(command)

    async def on_serial_data_message(self, message: SerialDataMessage) -> None:
        """Handle serial data from target"""
        try:
            log = self.query_one("#bolt-output", Log)
            log.write(message.data)
        except Exception:
            pass

    def _export_current_log(self) -> None:
        """Export current log to file"""
        timestamp = int(time.time())
        self._log_dir.mkdir(exist_ok=True)
        self._log_output(f"[*] Enable logging switch for file output")

    async def _save_current_profile(self) -> None:
        """Save current parameters as a profile"""
        self._log_output(f"[*] Profile save - length={self.glitch_config.length}, repeat={self.glitch_config.repeat}, delay={self.glitch_config.delay}")
        self._log_output("[*] Profile saving not yet implemented")

    # Scripting API methods
    def configure(self, length: int = None, repeat: int = None, delay: int = None) -> None:
        """Configure glitch parameters (for scripting API)"""
        if length is not None:
            self.glitch_config.length = length
            self._update_param_display("length", length)
        if repeat is not None:
            self.glitch_config.repeat = repeat
            self._update_param_display("repeat", repeat)
        if delay is not None:
            self.glitch_config.delay = delay
            self._update_param_display("delay", delay)

    def trigger(self) -> None:
        """Trigger a glitch (for scripting API)"""
        asyncio.create_task(self._trigger_glitch())

    def start_continuous(self) -> None:
        """Start continuous glitching (for scripting API)"""
        if not self.glitch_running:
            self._glitch_task = asyncio.create_task(self._start_continuous_glitch())

    def stop_continuous(self) -> None:
        """Stop continuous glitching (for scripting API)"""
        self._stop_continuous_glitch()
        if self._glitch_task:
            self._glitch_task.cancel()
            self._glitch_task = None

    def set_trigger(self, channel: int, edge: str, enabled: bool = True) -> None:
        """Set trigger configuration (for scripting API)"""
        if not 0 <= channel < 8:
            return

        if edge in ("^", "rising"):
            self.triggers[channel].edge = TriggerEdge.RISING
        elif edge in ("v", "falling"):
            self.triggers[channel].edge = TriggerEdge.FALLING
        else:
            self.triggers[channel].edge = TriggerEdge.DISABLED

        self.triggers[channel].enabled = enabled
        self._update_trigger_symbol(channel)

    # Profile management methods
    async def _load_selected_profile(self) -> None:
        """Load the selected glitch profile"""
        try:
            select = self.query_one("#profile-select", Select)
            profile_name = select.value

            if not profile_name or profile_name == Select.BLANK:
                self._log_output("[!] Select a profile")
                return

            profile = GLITCH_PROFILES.get(str(profile_name))
            if not profile:
                self._log_output(f"[!] Not found: {profile_name}")
                return

            self.current_profile = profile

            # Apply parameters
            if profile.successful_params:
                params = profile.successful_params[0]
                length = int(params.width_ns / self.CLOCK_PERIOD_NS)
                delay = int(params.offset_ns / self.CLOCK_PERIOD_NS)

                self.glitch_config.length = length
                self.glitch_config.delay = delay
                self._update_param_display("length", length)
                self._update_param_display("delay", delay)

                self._log_output(f"[+] Loaded: {profile.name}")
                self._log_output(f"    {profile.chip_family}")
                self._log_output(f"    width={params.width_ns}ns -> {length} cycles")
                self._log_output(f"    offset={params.offset_ns}ns -> {delay} cycles")

            elif profile.recommended_range:
                r = profile.recommended_range
                width_mid = (r.width_min + r.width_max) // 2
                offset_mid = (r.offset_min + r.offset_max) // 2

                length = int(width_mid / self.CLOCK_PERIOD_NS)
                delay = int(offset_mid / self.CLOCK_PERIOD_NS)

                self.glitch_config.length = length
                self.glitch_config.delay = delay
                self._update_param_display("length", length)
                self._update_param_display("delay", delay)

                self._log_output(f"[+] Loaded: {profile.name}")
                self._log_output(f"    Using midpoint of range")

        except Exception as e:
            self._log_output(f"[!] Load failed: {e}")

    async def _show_profile_info(self) -> None:
        """Show profile details"""
        try:
            select = self.query_one("#profile-select", Select)
            profile_name = select.value

            if not profile_name or profile_name == Select.BLANK:
                self._log_output("[!] Select a profile")
                return

            profile = GLITCH_PROFILES.get(str(profile_name))
            if not profile:
                self._log_output(f"[!] Not found: {profile_name}")
                return

            self._log_output("")
            self._log_output(f"=== {profile.name} ===")
            self._log_output(f"Chip: {profile.chip_family}")
            self._log_output(f"Attack: {profile.attack_type.name}")
            self._log_output(f"Target: {profile.target.value}")
            self._log_output(f"{profile.description}")

            if profile.successful_params:
                self._log_output("")
                self._log_output("Known params:")
                for i, p in enumerate(profile.successful_params[:3]):
                    self._log_output(f"  [{i}] w={p.width_ns}ns, o={p.offset_ns}ns")

            if profile.recommended_range:
                r = profile.recommended_range
                self._log_output("")
                self._log_output(f"Range: w={r.width_min}-{r.width_max}ns, o={r.offset_min}-{r.offset_max}ns")

            if profile.source:
                self._log_output(f"Source: {profile.source}")
            self._log_output("")

        except Exception as e:
            self._log_output(f"[!] Error: {e}")
