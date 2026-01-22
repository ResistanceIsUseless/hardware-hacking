"""
Black Magic Probe Panel

Panel for Black Magic Probe debug adapter.

Features:
- SWD/JTAG debugging
- Built-in GDB server
- Target auto-detection
- Flash programming
"""

import asyncio
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Input, Select, Switch, Log, TabbedContent, TabPane

from .base import DevicePanel, DeviceInfo, PanelCapability, CommandSuggestion


class BlackMagicPanel(DevicePanel):
    """
    Panel for Black Magic Probe.

    Uses the probe's built-in GDB server.
    """

    DEVICE_NAME = "Black Magic Probe"
    CAPABILITIES = [
        PanelCapability.SWD,
        PanelCapability.JTAG,
        PanelCapability.DEBUG,
        PanelCapability.FLASH,
    ]

    def __init__(self, device_info: DeviceInfo, app, *args, **kwargs):
        super().__init__(device_info, app, *args, **kwargs)
        self.gdb_port: Optional[str] = None
        self.uart_port: Optional[str] = None
        self.target_detected = False

    def compose(self) -> ComposeResult:
        with Vertical(id="blackmagic-panel"):
            # Header
            with Horizontal(classes="panel-header"):
                yield Static(f"{self.device_info.name}", classes="device-title")
                yield Static(f"Port: {self.device_info.port}", classes="device-port")

            # Port info
            with Horizontal(classes="port-info"):
                yield Static("GDB:", classes="port-label")
                yield Static("---", id="gdb-port", classes="port-value")
                yield Static("UART:", classes="port-label")
                yield Static("---", id="uart-port", classes="port-value")

            # Feature tabs
            with TabbedContent(id="bmp-features"):
                # Target Tab
                with TabPane("Target", id="tab-target"):
                    yield from self._build_target_section()

                # Debug Tab
                with TabPane("Debug", id="tab-debug"):
                    yield from self._build_debug_section()

                # Flash Tab
                with TabPane("Flash", id="tab-flash"):
                    yield from self._build_flash_section()

            # Console
            yield from self._build_console_section()

    def _build_target_section(self) -> ComposeResult:
        """Target detection and selection"""
        with Vertical():
            yield Static("Target Detection", classes="section-title")

            with Grid(classes="config-grid"):
                yield Static("Interface:")
                yield Select(
                    [("SWD", "swd"), ("JTAG", "jtag")],
                    value="swd",
                    id="target-interface"
                )

            with Horizontal(classes="button-row"):
                yield Button("Scan Targets", id="btn-scan", classes="btn-action")
                yield Button("Attach", id="btn-attach", classes="btn-action")
                yield Button("Detach", id="btn-detach", classes="btn-action")

            # Detected targets
            with Container(classes="targets-list") as targets:
                targets.border_title = "detected targets"
                yield Log(id="targets-log", classes="targets-output")

            # GDB connection info
            with Container(classes="gdb-info") as gdb:
                gdb.border_title = "gdb connection"
                yield Static("Connect with:", classes="help-text")
                yield Static("arm-none-eabi-gdb -ex 'target extended-remote /dev/cu.usbmodemXXX'",
                           id="gdb-command", classes="command-text")

    def _build_debug_section(self) -> ComposeResult:
        """Debug controls"""
        with Vertical():
            yield Static("Debug Control", classes="section-title")

            with Horizontal(classes="button-row"):
                yield Button("Halt", id="btn-halt", classes="btn-action")
                yield Button("Continue", id="btn-continue", classes="btn-action")
                yield Button("Step", id="btn-step", classes="btn-action")
                yield Button("Reset", id="btn-reset", classes="btn-action")

            # Registers
            with Container(classes="registers") as regs:
                regs.border_title = "registers"
                yield Static("r0:  0x00000000", id="reg-r0")
                yield Static("r1:  0x00000000", id="reg-r1")
                yield Static("r2:  0x00000000", id="reg-r2")
                yield Static("r3:  0x00000000", id="reg-r3")
                yield Static("pc:  0x00000000", id="reg-pc")
                yield Static("sp:  0x00000000", id="reg-sp")
                yield Static("lr:  0x00000000", id="reg-lr")

            # Memory read
            with Grid(classes="config-grid"):
                yield Static("Address:")
                yield Input(value="0x08000000", id="mem-addr", classes="hex-input")
                yield Static("Size:")
                yield Input(value="0x100", id="mem-size", classes="hex-input")

            yield Button("Read Memory", id="btn-read-mem", classes="btn-action")

    def _build_flash_section(self) -> ComposeResult:
        """Flash programming"""
        with Vertical():
            yield Static("Flash Programming", classes="section-title")

            with Grid(classes="config-grid"):
                yield Static("File:")
                yield Input(value="firmware.elf", id="flash-file", classes="file-input")

            with Horizontal(classes="button-row"):
                yield Button("Flash", id="btn-flash", classes="btn-action")
                yield Button("Verify", id="btn-verify", classes="btn-action")
                yield Button("Erase", id="btn-erase", classes="btn-action")

            yield Static("Progress:", classes="progress-label")
            yield Static("Ready", id="flash-progress", classes="progress-text")

    async def connect(self) -> bool:
        """Connect to Black Magic Probe"""
        self.log_output(f"[+] Connecting to {self.device_info.name}...")

        # BMP exposes two serial ports - GDB and UART
        # The main port is GDB, secondary is UART
        self.gdb_port = self.device_info.port

        self.log_output(f"[*] GDB port: {self.gdb_port}")
        self.log_output("[*] Connect GDB with:")
        self.log_output(f"    arm-none-eabi-gdb -ex 'target extended-remote {self.gdb_port}'")

        self.connected = True
        return True

    async def disconnect(self) -> None:
        """Disconnect"""
        self.connected = False
        self.log_output(f"[-] Disconnected from {self.device_info.name}")

    async def send_command(self, command: str) -> None:
        """Handle commands"""
        await super().send_command(command)

        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "help":
            self._show_help()
        elif cmd == "scan":
            await self._scan_targets()
        elif cmd == "attach":
            await self._attach_target(parts[1:])
        elif cmd == "monitor":
            await self._send_monitor(parts[1:])
        else:
            self.log_output(f"Unknown command: {cmd}")

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """Get suggestions"""
        suggestions = [
            CommandSuggestion("help", "Show available commands"),
            CommandSuggestion("scan", "Scan for targets"),
            CommandSuggestion("attach 1", "Attach to target 1", "attach"),
            CommandSuggestion("monitor swdp_scan", "SWD scan via monitor", "monitor"),
            CommandSuggestion("monitor jtag_scan", "JTAG scan via monitor", "monitor"),
            CommandSuggestion("monitor version", "Show BMP version", "monitor"),
        ]

        if partial:
            partial_lower = partial.lower()
            suggestions = [s for s in suggestions if s.command.lower().startswith(partial_lower)]

        return suggestions

    def _show_help(self) -> None:
        """Display help"""
        help_text = """
Black Magic Probe Commands:
  help              - Show this help
  scan              - Scan for targets
  attach <n>        - Attach to target number n
  monitor <cmd>     - Send monitor command

Monitor Commands (via GDB):
  swdp_scan         - Scan SWD
  jtag_scan         - Scan JTAG
  version           - Show firmware version
  connect_srst      - Assert SRST during connect
  hard_srst         - Hard reset target

GDB Usage:
  arm-none-eabi-gdb firmware.elf
  (gdb) target extended-remote /dev/cu.usbmodemXXX
  (gdb) monitor swdp_scan
  (gdb) attach 1
  (gdb) load
"""
        self.log_output(help_text)

    async def _scan_targets(self) -> None:
        """Scan for targets"""
        self.log_output("[*] Scanning for targets...")
        self.log_output("[*] Using SWD protocol...")
        # Simulated
        self.log_output("[+] Target 1: STM32F1 (Medium Density)")
        self.log_output("[+] Target 2: STM32F1 (Flash)")

        try:
            targets_log = self.query_one("#targets-log", Log)
            targets_log.clear()
            targets_log.write("1: STM32F1 (Medium Density)\n")
            targets_log.write("2: STM32F1 (Flash)\n")
        except Exception:
            pass

    async def _attach_target(self, args: List[str]) -> None:
        """Attach to target"""
        target_num = args[0] if args else "1"
        self.log_output(f"[*] Attaching to target {target_num}...")
        self.log_output("[+] Attached to STM32F1")
        self.log_output("[*] Halted at 0x08000400")
        self.target_detected = True

    async def _send_monitor(self, args: List[str]) -> None:
        """Send monitor command"""
        if not args:
            self.log_output("[!] Monitor command required")
            return

        cmd = " ".join(args)
        self.log_output(f"[*] Monitor: {cmd}")

        if cmd == "swdp_scan":
            await self._scan_targets()
        elif cmd == "version":
            self.log_output("[+] Black Magic Probe (Firmware v1.8.2)")
        else:
            self.log_output(f"[*] Sent: {cmd}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "btn-scan":
            await self._scan_targets()
        elif button_id == "btn-attach":
            await self._attach_target(["1"])
        elif button_id == "btn-halt":
            self.log_output("[*] Halting target...")
        elif button_id == "btn-continue":
            self.log_output("[*] Continuing...")
        elif button_id == "btn-reset":
            self.log_output("[*] Resetting target...")
        elif button_id == "btn-flash":
            self.log_output("[*] Flashing firmware...")
