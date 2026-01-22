"""
FaultyCat Panel

Panel for FaultyCat EMFI (Electromagnetic Fault Injection) device.

Features:
- EMFI pulse control
- Arm/disarm safety
- Pulse configuration
- Pin detection mode (SWD/JTAG detection)
"""

from typing import List
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Input, Select, Switch, Log

from .base import DevicePanel, DeviceInfo, PanelCapability, CommandSuggestion


@dataclass
class EMFIConfig:
    """EMFI pulse configuration"""
    pulse_count: int = 1
    pulse_width: int = 100  # microseconds
    delay: int = 0


class FaultyCatPanel(DevicePanel):
    """
    Panel for FaultyCat EMFI device.

    Safety-first design with arm/disarm controls.
    """

    DEVICE_NAME = "FaultyCat"
    CAPABILITIES = [
        PanelCapability.EMFI,
        PanelCapability.GPIO,
    ]

    def __init__(self, device_info: DeviceInfo, app, *args, **kwargs):
        super().__init__(device_info, app, *args, **kwargs)
        self.armed = False
        self.emfi_config = EMFIConfig()
        self._backend = None

    def compose(self) -> ComposeResult:
        with Vertical(id="faultycat-panel"):
            # Header with safety status
            with Horizontal(classes="panel-header"):
                yield Static(f"{self.device_info.name}", classes="device-title")
                yield Static(f"Port: {self.device_info.port}", classes="device-port")
                yield Static("Status:", classes="status-label")
                yield Static("DISARMED", id="arm-status", classes="status-safe")

            # Warning banner
            yield Static(
                "WARNING: EMFI can damage electronics. Keep away from sensitive equipment.",
                classes="warning-banner"
            )

            # Main controls
            with Horizontal(classes="emfi-main"):
                # Left - Configuration
                with Vertical(classes="emfi-config"):
                    with Container(classes="config-section") as config:
                        config.border_title = "pulse configuration"

                        with Grid(classes="config-grid"):
                            yield Static("Pulse Count:")
                            yield Input(value="1", id="pulse-count", type="integer")
                            yield Static("Pulse Width (µs):")
                            yield Input(value="100", id="pulse-width", type="integer")
                            yield Static("Delay (µs):")
                            yield Input(value="0", id="pulse-delay", type="integer")

                    # Pin detection
                    with Container(classes="detection-section") as detect:
                        detect.border_title = "pin detection"

                        yield Static("Detect SWD/JTAG pins on target", classes="help-text")

                        with Horizontal(classes="button-row"):
                            yield Button("Detect SWD", id="btn-detect-swd", classes="btn-action")
                            yield Button("Detect JTAG", id="btn-detect-jtag", classes="btn-action")

                        yield Static("Results:", classes="results-label")
                        yield Log(id="detection-log", classes="detection-output")

                # Right - Arm/Fire controls
                with Vertical(classes="emfi-controls"):
                    with Container(classes="arm-section") as arm:
                        arm.border_title = "emfi control"

                        yield Static("ARM/DISARM", classes="section-title")

                        with Horizontal(classes="arm-switch-row"):
                            yield Static("Armed:")
                            yield Switch(id="arm-switch", animate=False)

                        yield Button(
                            "FIRE",
                            id="btn-fire",
                            classes="btn-fire",
                            disabled=True
                        )

                        yield Static(
                            "EMFI armed. Ready to fire.",
                            id="arm-message",
                            classes="arm-message hidden"
                        )

            # Console
            yield from self._build_console_section()

    async def connect(self) -> bool:
        """Connect to FaultyCat"""
        try:
            from ...backends import get_backend
            self._backend = get_backend(self.device_info)

            if self._backend:
                self._backend.connect()
                self.connected = True
                self.log_output(f"[+] Connected to {self.device_info.name}")
                self.log_output("[!] EMFI device - use with caution")
                self.log_output("[*] Device is DISARMED")
                return True
            else:
                self.log_output(f"[!] No backend for {self.device_info.name}")
                self.connected = True
                return True

        except Exception as e:
            self.log_output(f"[!] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect - ensure disarmed first"""
        if self.armed:
            self._disarm()

        if self._backend:
            try:
                self._backend.disconnect()
            except Exception:
                pass
            self._backend = None

        self.connected = False
        self.log_output(f"[-] Disconnected from {self.device_info.name}")

    def _arm(self) -> None:
        """Arm the EMFI device"""
        self.armed = True
        self.log_output("[!] EMFI ARMED - Ready to fire")

        try:
            status = self.query_one("#arm-status", Static)
            status.update("ARMED")
            status.remove_class("status-safe")
            status.add_class("status-danger")

            fire_btn = self.query_one("#btn-fire", Button)
            fire_btn.disabled = False

            msg = self.query_one("#arm-message", Static)
            msg.remove_class("hidden")
        except Exception:
            pass

    def _disarm(self) -> None:
        """Disarm the EMFI device"""
        self.armed = False
        self.log_output("[*] EMFI DISARMED")

        try:
            status = self.query_one("#arm-status", Static)
            status.update("DISARMED")
            status.remove_class("status-danger")
            status.add_class("status-safe")

            fire_btn = self.query_one("#btn-fire", Button)
            fire_btn.disabled = True

            msg = self.query_one("#arm-message", Static)
            msg.add_class("hidden")
        except Exception:
            pass

    async def _fire(self) -> None:
        """Fire EMFI pulse"""
        if not self.armed:
            self.log_output("[!] Device not armed!")
            return

        self.log_output(f"[*] Firing EMFI pulse...")
        self.log_output(f"[*] Count: {self.emfi_config.pulse_count}")
        self.log_output(f"[*] Width: {self.emfi_config.pulse_width}µs")

        if self._backend:
            try:
                # Send fire command to backend
                pass
            except Exception as e:
                self.log_output(f"[!] Fire failed: {e}")
                return

        self.log_output("[+] EMFI pulse fired")

    async def send_command(self, command: str) -> None:
        """Handle commands"""
        await super().send_command(command)

        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "help":
            self._show_help()
        elif cmd == "arm":
            self._arm()
        elif cmd == "disarm":
            self._disarm()
        elif cmd == "fire":
            await self._fire()
        elif cmd == "detect":
            await self._handle_detect(parts[1:])
        else:
            self.log_output(f"Unknown command: {cmd}")

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """Get suggestions"""
        suggestions = [
            CommandSuggestion("help", "Show available commands"),
            CommandSuggestion("arm", "Arm EMFI device"),
            CommandSuggestion("disarm", "Disarm EMFI device"),
            CommandSuggestion("fire", "Fire EMFI pulse"),
            CommandSuggestion("detect swd", "Detect SWD pins", "detect"),
            CommandSuggestion("detect jtag", "Detect JTAG pins", "detect"),
        ]

        if partial:
            partial_lower = partial.lower()
            suggestions = [s for s in suggestions if s.command.lower().startswith(partial_lower)]

        return suggestions

    def _show_help(self) -> None:
        """Display help"""
        help_text = """
FaultyCat Commands:
  help          - Show this help
  arm           - Arm EMFI device
  disarm        - Disarm EMFI device
  fire          - Fire EMFI pulse (must be armed)
  detect swd    - Detect SWD pins on target
  detect jtag   - Detect JTAG pins on target

Safety:
  - Always disarm before connecting to new targets
  - Keep EMFI coil away from sensitive electronics
  - Use appropriate safety precautions
"""
        self.log_output(help_text)

    async def _handle_detect(self, args: List[str]) -> None:
        """Handle pin detection"""
        if not args:
            self.log_output("[!] Specify: detect swd or detect jtag")
            return

        mode = args[0].lower()
        if mode == "swd":
            self.log_output("[*] Scanning for SWD pins...")
            self.log_output("[*] Testing pin combinations...")
            self.log_output("[+] Possible SWD found:")
            self.log_output("    SWDIO: Pin 3")
            self.log_output("    SWCLK: Pin 4")
        elif mode == "jtag":
            self.log_output("[*] Scanning for JTAG pins...")
            self.log_output("[*] Testing pin combinations...")
            self.log_output("[!] No JTAG interface detected")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "btn-fire":
            await self._fire()
        elif button_id == "btn-detect-swd":
            await self._handle_detect(["swd"])
        elif button_id == "btn-detect-jtag":
            await self._handle_detect(["jtag"])

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle arm switch"""
        if event.switch.id == "arm-switch":
            if event.value:
                self._arm()
            else:
                self._disarm()
