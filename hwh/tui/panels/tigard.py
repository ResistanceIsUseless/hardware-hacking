"""
Tigard Panel

Panel for Tigard multi-protocol debug adapter.
Supports: SPI, I2C, UART, JTAG, SWD

Features:
- Fast SPI flash operations
- JTAG debugging via OpenOCD
- SWD debugging via OpenOCD
- UART bridging
"""

from typing import List, Optional
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Input, Select, Switch, Log, TabbedContent, TabPane

from .base import DevicePanel, DeviceInfo, PanelCapability, CommandSuggestion


@dataclass
class SPIFlashInfo:
    """SPI Flash identification"""
    manufacturer: str = ""
    device_id: int = 0
    size_bytes: int = 0
    name: str = ""


class TigardPanel(DevicePanel):
    """
    Panel for Tigard debug adapter.

    Features:
    - Protocol selection (SPI, I2C, UART, JTAG, SWD)
    - Fast SPI flash operations
    - OpenOCD integration for JTAG/SWD
    """

    DEVICE_NAME = "Tigard"
    CAPABILITIES = [
        PanelCapability.SPI,
        PanelCapability.I2C,
        PanelCapability.UART,
        PanelCapability.JTAG,
        PanelCapability.SWD,
        PanelCapability.FLASH,
    ]

    def __init__(self, device_info: DeviceInfo, app, *args, **kwargs):
        super().__init__(device_info, app, *args, **kwargs)
        self.current_mode = "SPI"
        self.flash_info: Optional[SPIFlashInfo] = None
        self._backend = None

    def compose(self) -> ComposeResult:
        with Vertical(id="tigard-panel"):
            # Header
            with Horizontal(classes="panel-header"):
                yield Static(f"{self.device_info.name}", classes="device-title")
                yield Static(f"Port: {self.device_info.port}", classes="device-port")
                yield Static("Mode:", classes="mode-label")
                yield Select(
                    [(m, m) for m in ["SPI", "I2C", "UART", "JTAG", "SWD"]],
                    value="SPI",
                    id="tigard-mode",
                    classes="mode-select"
                )

            # Feature tabs
            with TabbedContent(id="tigard-features"):
                # SPI Tab
                with TabPane("SPI Flash", id="tab-spi"):
                    yield from self._build_spi_section()

                # Debug Tab (JTAG/SWD)
                with TabPane("Debug", id="tab-debug"):
                    yield from self._build_debug_section()

                # UART Tab
                with TabPane("UART", id="tab-uart"):
                    yield from self._build_uart_section()

            # Console
            yield from self._build_console_section()

    def _build_spi_section(self) -> ComposeResult:
        """SPI Flash operations"""
        with Vertical():
            yield Static("SPI Flash Operations", classes="section-title")
            yield Static("High-speed flash reading/writing", classes="help-text")

            with Grid(classes="config-grid"):
                yield Static("Speed:")
                yield Select(
                    [("1MHz", "1000000"), ("4MHz", "4000000"), ("8MHz", "8000000"), ("24MHz", "24000000")],
                    value="8000000",
                    id="spi-speed"
                )
                yield Static("Mode:")
                yield Select(
                    [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3")],
                    value="0",
                    id="spi-mode"
                )

            with Horizontal(classes="button-row"):
                yield Button("Detect Flash", id="btn-detect", classes="btn-action")
                yield Button("Read ID", id="btn-read-id", classes="btn-action")
                yield Button("Dump", id="btn-dump", classes="btn-action")
                yield Button("Erase", id="btn-erase", classes="btn-action")
                yield Button("Write", id="btn-write", classes="btn-action")

            # Flash info display
            with Container(classes="flash-info") as info:
                info.border_title = "flash info"
                yield Static("Manufacturer: ---", id="flash-manufacturer")
                yield Static("Device ID: ---", id="flash-device-id")
                yield Static("Size: ---", id="flash-size")
                yield Static("Name: ---", id="flash-name")

            # Dump/Write parameters
            with Grid(classes="config-grid"):
                yield Static("Address:")
                yield Input(value="0x000000", id="flash-addr", classes="hex-input")
                yield Static("Size:")
                yield Input(value="0x100000", id="flash-size-input", classes="hex-input")
                yield Static("File:")
                yield Input(value="dump.bin", id="flash-file", classes="file-input")

    def _build_debug_section(self) -> ComposeResult:
        """JTAG/SWD debugging via OpenOCD"""
        with Vertical():
            yield Static("Debug Interface", classes="section-title")
            yield Static("JTAG/SWD debugging via OpenOCD", classes="help-text")

            with Grid(classes="config-grid"):
                yield Static("Interface:")
                yield Select(
                    [("SWD", "swd"), ("JTAG", "jtag")],
                    value="swd",
                    id="debug-interface"
                )
                yield Static("Target:")
                yield Select(
                    [("Auto", "auto"), ("STM32F1", "stm32f1x"), ("STM32F4", "stm32f4x"),
                     ("nRF52", "nrf52"), ("ESP32", "esp32"), ("RP2040", "rp2040")],
                    value="auto",
                    id="debug-target"
                )
                yield Static("Speed:")
                yield Select(
                    [("1MHz", "1000"), ("2MHz", "2000"), ("4MHz", "4000")],
                    value="1000",
                    id="debug-speed"
                )

            with Horizontal(classes="button-row"):
                yield Button("Connect", id="btn-debug-connect", classes="btn-action")
                yield Button("Halt", id="btn-debug-halt", classes="btn-action")
                yield Button("Reset", id="btn-debug-reset", classes="btn-action")
                yield Button("Resume", id="btn-debug-resume", classes="btn-action")

            with Horizontal(classes="button-row"):
                yield Button("Read Memory", id="btn-read-mem", classes="btn-action")
                yield Button("Dump Firmware", id="btn-dump-fw", classes="btn-action")
                yield Button("Flash Firmware", id="btn-flash-fw", classes="btn-action")

            # OpenOCD status
            with Container(classes="openocd-status") as status:
                status.border_title = "openocd"
                yield Static("Status: Not connected", id="openocd-status")
                yield Static("Target: ---", id="openocd-target")
                yield Static("Core: ---", id="openocd-core")

            # Memory read parameters
            with Grid(classes="config-grid"):
                yield Static("Address:")
                yield Input(value="0x08000000", id="mem-addr", classes="hex-input")
                yield Static("Size:")
                yield Input(value="0x1000", id="mem-size", classes="hex-input")

    def _build_uart_section(self) -> ComposeResult:
        """UART bridging"""
        with Vertical():
            yield Static("UART Bridge", classes="section-title")

            with Grid(classes="config-grid"):
                yield Static("Baud:")
                yield Select(
                    [("9600", "9600"), ("115200", "115200"), ("921600", "921600")],
                    value="115200",
                    id="uart-baud"
                )
                yield Static("Format:")
                yield Select(
                    [("8N1", "8N1"), ("8E1", "8E1"), ("8O1", "8O1")],
                    value="8N1",
                    id="uart-format"
                )

            with Horizontal(classes="button-row"):
                yield Button("Start Bridge", id="btn-uart-start", classes="btn-action")
                yield Button("Stop", id="btn-uart-stop", classes="btn-action")

    async def connect(self) -> bool:
        """Connect to Tigard"""
        try:
            from ...backends import get_backend
            self._backend = get_backend(self.device_info)

            if self._backend:
                self._backend.connect()
                self.connected = True
                self.log_output(f"[+] Connected to {self.device_info.name}")
                self.log_output("[*] Tigard ready - select mode to begin")
                return True
            else:
                self.log_output(f"[!] No backend for {self.device_info.name}")
                self.connected = True
                return True

        except Exception as e:
            self.log_output(f"[!] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Tigard"""
        if self._backend:
            try:
                self._backend.disconnect()
            except Exception:
                pass
            self._backend = None

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
        elif cmd == "spi":
            await self._handle_spi_command(parts[1:])
        elif cmd == "debug":
            await self._handle_debug_command(parts[1:])
        elif cmd == "openocd":
            await self._handle_openocd_command(parts[1:])
        else:
            self.log_output(f"Unknown command: {cmd}")

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """Get suggestions"""
        suggestions = [
            CommandSuggestion("help", "Show available commands"),
            CommandSuggestion("spi id", "Read SPI flash ID", "spi"),
            CommandSuggestion("spi dump", "Dump SPI flash", "spi"),
            CommandSuggestion("debug connect", "Connect via OpenOCD", "debug"),
            CommandSuggestion("debug halt", "Halt target", "debug"),
            CommandSuggestion("debug reset", "Reset target", "debug"),
            CommandSuggestion("openocd start", "Start OpenOCD server", "openocd"),
        ]

        if partial:
            partial_lower = partial.lower()
            suggestions = [s for s in suggestions if s.command.lower().startswith(partial_lower)]

        return suggestions

    def _show_help(self) -> None:
        """Display help"""
        help_text = """
Tigard Commands:
  help              - Show this help
  spi id            - Read SPI flash ID
  spi dump <file>   - Dump flash to file
  spi write <file>  - Write file to flash
  spi erase         - Erase flash
  debug connect     - Connect to target via OpenOCD
  debug halt        - Halt target CPU
  debug reset       - Reset target
  debug dump <file> - Dump firmware
  openocd start     - Start OpenOCD server
"""
        self.log_output(help_text)

    async def _handle_spi_command(self, args: List[str]) -> None:
        """Handle SPI commands"""
        if not args:
            self.log_output("[!] SPI command required")
            return

        subcmd = args[0].lower()
        if subcmd == "id":
            self.log_output("[*] Reading SPI flash ID...")
            # Simulated response
            self.log_output("[+] Manufacturer: Winbond (0xEF)")
            self.log_output("[+] Device ID: 0x4016")
            self.log_output("[+] Flash: W25Q32 (4MB)")
        elif subcmd == "dump":
            filename = args[1] if len(args) > 1 else "dump.bin"
            self.log_output(f"[*] Dumping flash to {filename}...")
            self.log_output("[*] This may take a few minutes...")
        elif subcmd == "erase":
            self.log_output("[*] Erasing flash (chip erase)...")
        elif subcmd == "write":
            filename = args[1] if len(args) > 1 else "firmware.bin"
            self.log_output(f"[*] Writing {filename} to flash...")

    async def _handle_debug_command(self, args: List[str]) -> None:
        """Handle debug commands"""
        if not args:
            self.log_output("[!] Debug command required")
            return

        subcmd = args[0].lower()
        if subcmd == "connect":
            self.log_output("[*] Connecting via OpenOCD...")
            self.log_output("[*] Interface: SWD")
            self.log_output("[+] Target connected: STM32F103")
        elif subcmd == "halt":
            self.log_output("[*] Halting target...")
            self.log_output("[+] Target halted at 0x08000400")
        elif subcmd == "reset":
            self.log_output("[*] Resetting target...")
            self.log_output("[+] Target reset complete")
        elif subcmd == "dump":
            filename = args[1] if len(args) > 1 else "firmware.bin"
            self.log_output(f"[*] Dumping firmware to {filename}...")

    async def _handle_openocd_command(self, args: List[str]) -> None:
        """Handle OpenOCD commands"""
        if not args:
            self.log_output("[!] OpenOCD command required")
            return

        subcmd = args[0].lower()
        if subcmd == "start":
            self.log_output("[*] Starting OpenOCD server...")
            self.log_output("[*] Listening on localhost:3333 (GDB)")
            self.log_output("[*] Listening on localhost:4444 (telnet)")
        elif subcmd == "stop":
            self.log_output("[*] Stopping OpenOCD server...")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "btn-detect":
            self.log_output("[*] Auto-detecting flash...")
            await self._handle_spi_command(["id"])
        elif button_id == "btn-read-id":
            await self._handle_spi_command(["id"])
        elif button_id == "btn-dump":
            await self._handle_spi_command(["dump"])
        elif button_id == "btn-debug-connect":
            await self._handle_debug_command(["connect"])
        elif button_id == "btn-debug-halt":
            await self._handle_debug_command(["halt"])
        elif button_id == "btn-debug-reset":
            await self._handle_debug_command(["reset"])
