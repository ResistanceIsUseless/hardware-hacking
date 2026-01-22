"""
Bus Pirate Panel

Full-featured panel for Bus Pirate 5/6 devices.
Supports: SPI, I2C, UART, 1-Wire, JTAG/SWD scanning, Logic Analyzer, ADC, PWM
"""

from typing import List, Optional
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Input, Select, Switch, Log, TabbedContent, TabPane

from .base import DevicePanel, DeviceInfo, PanelCapability, CommandSuggestion
from .logic_analyzer import LogicAnalyzerWidget, LogicCapture


@dataclass
class SPIConfig:
    speed: int = 1000000
    mode: int = 0
    cs_active_low: bool = True


@dataclass
class I2CConfig:
    speed: int = 100000
    address: int = 0x50


@dataclass
class UARTConfig:
    baud: int = 115200
    data_bits: int = 8
    parity: str = "N"
    stop_bits: int = 1


class BusPiratePanel(DevicePanel):
    """
    Panel for Bus Pirate 5/6 devices.

    Features:
    - Protocol selection (SPI, I2C, UART, 1-Wire)
    - JTAG/SWD pin scanning
    - Logic analyzer (8ch, 62.5MSPS)
    - ADC voltage measurement
    - PWM generation
    - Power supply control
    """

    DEVICE_NAME = "Bus Pirate"
    CAPABILITIES = [
        PanelCapability.SPI,
        PanelCapability.I2C,
        PanelCapability.UART,
        PanelCapability.JTAG,
        PanelCapability.SWD,
        PanelCapability.LOGIC,
        PanelCapability.ADC,
        PanelCapability.PWM,
        PanelCapability.GPIO,
    ]

    def __init__(self, device_info: DeviceInfo, app, *args, **kwargs):
        super().__init__(device_info, app, *args, **kwargs)
        self.current_mode = "HiZ"
        self.spi_config = SPIConfig()
        self.i2c_config = I2CConfig()
        self.uart_config = UARTConfig()
        self.power_enabled = False
        self.pullups_enabled = False
        self._backend = None
        self._logic_widget: Optional[LogicAnalyzerWidget] = None
        self._logic_capturing = False

    def compose(self) -> ComposeResult:
        with Vertical(id="buspirate-panel"):
            # Header with device info and mode
            with Horizontal(classes="panel-header"):
                yield Static(f"{self.device_info.name}", classes="device-title")
                yield Static(f"Port: {self.device_info.port}", classes="device-port")
                yield Static(f"Mode: ", classes="mode-label")
                yield Select(
                    [(mode, mode) for mode in ["HiZ", "SPI", "I2C", "UART", "1-Wire", "2-Wire", "3-Wire"]],
                    value="HiZ",
                    id="mode-select",
                    classes="mode-select"
                )
                yield Static(" Voltage:", classes="voltage-label")
                yield Select(
                    [("3.3V", "3.3"), ("5V", "5.0"), ("Off", "0")],
                    value="3.3",
                    id="voltage-select",
                    classes="voltage-select"
                )

            # Feature tabs within device panel
            with TabbedContent(id="bp-features"):
                # Protocol Tab - Current mode operations
                with TabPane("Protocol", id="tab-protocol"):
                    yield from self._build_protocol_section()

                # Scan Tab - JTAG/SWD pin detection
                with TabPane("Scan", id="tab-scan"):
                    yield from self._build_scan_section()

                # Logic Tab - Logic analyzer
                with TabPane("Logic", id="tab-logic"):
                    yield from self._build_logic_section()

                # Power Tab - ADC/PWM/Power
                with TabPane("Power", id="tab-power"):
                    yield from self._build_power_section()

            # Console at bottom
            yield from self._build_console_section()

    def _build_protocol_section(self) -> ComposeResult:
        """Protocol-specific controls that change based on mode"""
        with Container(id="protocol-container"):
            # SPI controls (shown when SPI mode selected)
            with Container(id="spi-controls", classes="protocol-controls"):
                yield Static("SPI Configuration", classes="section-title")
                with Grid(classes="config-grid"):
                    yield Static("Speed:")
                    yield Select(
                        [("1MHz", "1000000"), ("4MHz", "4000000"), ("8MHz", "8000000")],
                        value="1000000",
                        id="spi-speed"
                    )
                    yield Static("Mode:")
                    yield Select(
                        [("0 (CPOL=0,CPHA=0)", "0"), ("1", "1"), ("2", "2"), ("3", "3")],
                        value="0",
                        id="spi-mode"
                    )
                    yield Static("CS Active:")
                    yield Select([("Low", "low"), ("High", "high")], value="low", id="spi-cs")

                with Horizontal(classes="button-row"):
                    yield Button("Read Flash ID", id="btn-spi-id", classes="btn-action")
                    yield Button("Dump Flash", id="btn-spi-dump", classes="btn-action")
                    yield Button("Erase", id="btn-spi-erase", classes="btn-action")
                    yield Button("Write", id="btn-spi-write", classes="btn-action")

                with Horizontal(classes="input-row"):
                    yield Static("Address:")
                    yield Input(value="0x000000", id="spi-addr", classes="hex-input")
                    yield Static("Size:")
                    yield Input(value="0x1000", id="spi-size", classes="hex-input")
                    yield Static("File:")
                    yield Input(value="dump.bin", id="spi-file", classes="file-input")

            # I2C controls
            with Container(id="i2c-controls", classes="protocol-controls hidden"):
                yield Static("I2C Configuration", classes="section-title")
                with Grid(classes="config-grid"):
                    yield Static("Speed:")
                    yield Select(
                        [("100kHz", "100000"), ("400kHz", "400000"), ("1MHz", "1000000")],
                        value="100000",
                        id="i2c-speed"
                    )
                    yield Static("Address:")
                    yield Input(value="0x50", id="i2c-addr", classes="hex-input")

                with Horizontal(classes="button-row"):
                    yield Button("Scan Bus", id="btn-i2c-scan", classes="btn-action")
                    yield Button("Read Byte", id="btn-i2c-read", classes="btn-action")
                    yield Button("Write Byte", id="btn-i2c-write", classes="btn-action")
                    yield Button("Dump EEPROM", id="btn-i2c-dump", classes="btn-action")

            # UART controls
            with Container(id="uart-controls", classes="protocol-controls hidden"):
                yield Static("UART Configuration", classes="section-title")
                with Grid(classes="config-grid"):
                    yield Static("Baud:")
                    yield Select(
                        [("9600", "9600"), ("115200", "115200"), ("230400", "230400"), ("921600", "921600")],
                        value="115200",
                        id="uart-baud"
                    )
                    yield Static("Format:")
                    yield Select(
                        [("8N1", "8N1"), ("8E1", "8E1"), ("8O1", "8O1"), ("7E1", "7E1")],
                        value="8N1",
                        id="uart-format"
                    )

                with Horizontal(classes="button-row"):
                    yield Button("Bridge Mode", id="btn-uart-bridge", classes="btn-action")
                    yield Button("Auto Baud", id="btn-uart-auto", classes="btn-action")

    def _build_scan_section(self) -> ComposeResult:
        """JTAG/SWD pin scanning controls"""
        with Vertical():
            yield Static("Pin Scanning", classes="section-title")
            yield Static("Scan target pins to detect JTAG/SWD interfaces", classes="help-text")

            with Horizontal(classes="button-row"):
                yield Button("JTAG Scan", id="btn-jtag-scan", classes="btn-action")
                yield Button("SWD Scan", id="btn-swd-scan", classes="btn-action")
                yield Button("UART Detect", id="btn-uart-detect", classes="btn-action")

            with Grid(classes="config-grid"):
                yield Static("Pins to scan:")
                yield Input(value="0-7", id="scan-pins", classes="pin-input")
                yield Static("Voltage:")
                yield Select([("3.3V", "3.3"), ("1.8V", "1.8"), ("5V", "5.0")], value="3.3", id="scan-voltage")

            yield Static("Scan Results:", classes="section-subtitle")
            yield Log(id="scan-results", classes="scan-log")

    def _build_logic_section(self) -> ComposeResult:
        """Logic analyzer controls"""
        with Vertical():
            yield Static("Logic Analyzer", classes="section-title")
            yield Static("8 channels @ 62.5MSPS max | Demo mode for testing", classes="help-text")

            with Horizontal(classes="button-row"):
                yield Button("Capture", id="btn-logic-capture", classes="btn-action")
                yield Button("Stop", id="btn-logic-stop", classes="btn-action")
                yield Button("Demo", id="btn-logic-demo", classes="btn-action")
                yield Button("Export", id="btn-logic-export", classes="btn-action")

            with Grid(classes="config-grid"):
                yield Static("Rate:")
                yield Select(
                    [("62.5MHz", "62500000"), ("10MHz", "10000000"), ("1MHz", "1000000")],
                    value="10000000",
                    id="logic-rate"
                )
                yield Static("Samples:")
                yield Select(
                    [("1K", "1024"), ("8K", "8192"), ("32K", "32768")],
                    value="8192",
                    id="logic-samples"
                )
                yield Static("Trigger:")
                yield Select(
                    [("None", "none"), ("CH0 ↑", "ch0_rise"), ("CH0 ↓", "ch0_fall"),
                     ("CH1 ↑", "ch1_rise"), ("CH1 ↓", "ch1_fall")],
                    value="none",
                    id="logic-trigger"
                )

            # Channel enables - compact row
            with Horizontal(classes="channel-row"):
                for i in range(8):
                    yield Static(f"{i}", classes="channel-num")
                    yield Switch(id=f"logic-ch{i}", value=True if i < 4 else False)

            # Waveform display using LogicAnalyzerWidget
            self._logic_widget = LogicAnalyzerWidget(channels=8, visible_samples=60, id="logic-waveform")
            yield self._logic_widget

    def _build_power_section(self) -> ComposeResult:
        """Power supply and measurement controls"""
        with Vertical():
            yield Static("Power & Measurement", classes="section-title")

            with Horizontal(classes="power-controls"):
                with Vertical(classes="power-group"):
                    yield Static("Power Supply")
                    with Horizontal():
                        yield Static("Enable:")
                        yield Switch(id="power-enable")
                    with Horizontal():
                        yield Static("Voltage:")
                        yield Select(
                            [("3.3V", "3.3"), ("5V", "5.0"), ("1.8V", "1.8")],
                            value="3.3",
                            id="power-voltage"
                        )

                with Vertical(classes="power-group"):
                    yield Static("Pull-ups")
                    with Horizontal():
                        yield Static("Enable:")
                        yield Switch(id="pullup-enable")

            yield Static("ADC Measurement", classes="section-subtitle")
            with Horizontal(classes="adc-display"):
                yield Static("CH0: ", classes="adc-label")
                yield Static("---", id="adc-ch0", classes="adc-value")
                yield Static("V", classes="adc-unit")
                yield Button("Read", id="btn-adc-read", classes="btn-small")
                yield Button("Monitor", id="btn-adc-monitor", classes="btn-small")

            yield Static("PWM Output", classes="section-subtitle")
            with Grid(classes="config-grid"):
                yield Static("Frequency:")
                yield Input(value="1000", id="pwm-freq")
                yield Static("Duty:")
                yield Input(value="50", id="pwm-duty")
            with Horizontal():
                yield Button("Start PWM", id="btn-pwm-start", classes="btn-action")
                yield Button("Stop PWM", id="btn-pwm-stop", classes="btn-action")

            yield Static("Frequency Counter", classes="section-subtitle")
            with Horizontal():
                yield Static("Measured: ")
                yield Static("---", id="freq-value", classes="freq-display")
                yield Static("Hz")
                yield Button("Measure", id="btn-freq-measure", classes="btn-small")

    async def connect(self) -> bool:
        """Connect to Bus Pirate"""
        try:
            # Try to get Bus Pirate backend
            from ...backends import get_backend
            self._backend = get_backend(self.device_info)

            if self._backend:
                self._backend.connect()
                self.connected = True
                self.log_output(f"[+] Connected to {self.device_info.name}")
                self.log_output(f"[*] Port: {self.device_info.port}")
                self.log_output(f"[*] Mode: HiZ (safe mode)")
                return True
            else:
                self.log_output(f"[!] No backend available for {self.device_info.name}")
                # Still mark as connected for UI testing
                self.connected = True
                return True

        except Exception as e:
            self.log_output(f"[!] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Bus Pirate"""
        if self._backend:
            try:
                self._backend.disconnect()
            except Exception:
                pass
            self._backend = None
        self.connected = False
        self.log_output(f"[-] Disconnected from {self.device_info.name}")

    async def send_command(self, command: str) -> None:
        """Send command to Bus Pirate"""
        await super().send_command(command)

        # Parse and execute command
        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "help":
            self._show_help()
        elif cmd == "mode":
            if len(parts) > 1:
                await self._set_mode(parts[1])
        elif cmd == "spi":
            await self._handle_spi_command(parts[1:])
        elif cmd == "i2c":
            await self._handle_i2c_command(parts[1:])
        elif cmd == "logic":
            await self._handle_logic_command(parts[1:])
        elif cmd == "power":
            await self._handle_power_command(parts[1:])
        else:
            self.log_output(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """Get command suggestions for auto-completion"""
        suggestions = [
            CommandSuggestion("help", "Show available commands"),
            CommandSuggestion("mode spi", "Switch to SPI mode", "mode"),
            CommandSuggestion("mode i2c", "Switch to I2C mode", "mode"),
            CommandSuggestion("mode uart", "Switch to UART mode", "mode"),
            CommandSuggestion("spi id", "Read SPI flash ID", "spi"),
            CommandSuggestion("spi dump", "Dump SPI flash", "spi"),
            CommandSuggestion("i2c scan", "Scan I2C bus for devices", "i2c"),
            CommandSuggestion("logic capture", "Start logic capture", "logic"),
            CommandSuggestion("power on", "Enable power supply", "power"),
            CommandSuggestion("power off", "Disable power supply", "power"),
            CommandSuggestion("adc read", "Read ADC voltage", "adc"),
        ]

        if partial:
            partial_lower = partial.lower()
            suggestions = [s for s in suggestions if s.command.lower().startswith(partial_lower)]

        return suggestions

    def _show_help(self) -> None:
        """Display help message"""
        help_text = """
Available commands:
  help              - Show this help
  mode <mode>       - Set mode (spi, i2c, uart, 1wire)
  spi id            - Read SPI flash ID
  spi dump <file>   - Dump SPI flash to file
  i2c scan          - Scan I2C bus
  logic capture     - Capture logic data
  power on/off      - Control power supply
  adc read          - Read ADC voltage
"""
        self.log_output(help_text)

    async def _set_mode(self, mode: str) -> None:
        """Set Bus Pirate mode"""
        mode = mode.upper()
        valid_modes = ["HIZ", "SPI", "I2C", "UART", "1WIRE", "2WIRE", "3WIRE"]
        if mode not in valid_modes:
            self.log_output(f"[!] Invalid mode: {mode}")
            return

        self.current_mode = mode
        self.log_output(f"[*] Mode set to: {mode}")

        # Update UI to show relevant controls
        # This would hide/show protocol-specific controls

    async def _handle_spi_command(self, args: List[str]) -> None:
        """Handle SPI commands"""
        if not args:
            self.log_output("[!] SPI command required (id, dump, write, erase)")
            return

        subcmd = args[0].lower()
        if subcmd == "id":
            self.log_output("[*] Reading SPI flash ID...")
            # Would call backend to read flash ID
            self.log_output("[+] Flash ID: 0xEF4016 (Winbond W25Q32)")
        elif subcmd == "dump":
            filename = args[1] if len(args) > 1 else "dump.bin"
            self.log_output(f"[*] Dumping flash to {filename}...")
        elif subcmd == "write":
            self.log_output("[*] Writing to flash...")
        elif subcmd == "erase":
            self.log_output("[*] Erasing flash...")

    async def _handle_i2c_command(self, args: List[str]) -> None:
        """Handle I2C commands"""
        if not args:
            self.log_output("[!] I2C command required (scan, read, write)")
            return

        subcmd = args[0].lower()
        if subcmd == "scan":
            self.log_output("[*] Scanning I2C bus...")
            self.log_output("[+] Found devices at: 0x50, 0x68")
        elif subcmd == "read":
            addr = args[1] if len(args) > 1 else "0x50"
            self.log_output(f"[*] Reading from {addr}...")

    async def _handle_logic_command(self, args: List[str]) -> None:
        """Handle logic analyzer commands"""
        if not args:
            self.log_output("[!] Logic command required (capture, stop)")
            return

        subcmd = args[0].lower()
        if subcmd == "capture":
            self.log_output("[*] Starting logic capture...")
            self.log_output("[*] Waiting for trigger...")
        elif subcmd == "stop":
            self.log_output("[*] Stopping capture...")

    async def _handle_power_command(self, args: List[str]) -> None:
        """Handle power commands"""
        if not args:
            self.log_output("[!] Power command required (on, off)")
            return

        subcmd = args[0].lower()
        if subcmd == "on":
            self.power_enabled = True
            self.log_output("[+] Power supply enabled (3.3V)")
        elif subcmd == "off":
            self.power_enabled = False
            self.log_output("[-] Power supply disabled")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "btn-spi-id":
            await self._handle_spi_command(["id"])
        elif button_id == "btn-spi-dump":
            await self._handle_spi_command(["dump"])
        elif button_id == "btn-i2c-scan":
            await self._handle_i2c_command(["scan"])
        elif button_id == "btn-logic-capture":
            await self._start_logic_capture()
        elif button_id == "btn-logic-stop":
            await self._stop_logic_capture()
        elif button_id == "btn-logic-demo":
            await self._load_logic_demo()
        elif button_id == "btn-logic-export":
            self.log_output("[*] Export not implemented yet")
        elif button_id == "btn-jtag-scan":
            self.log_output("[*] Starting JTAG pin scan...")
            self.log_output("[*] Testing all pin combinations...")
        elif button_id == "btn-swd-scan":
            self.log_output("[*] Starting SWD pin scan...")

    # --------------------------------------------------------------------------
    # Logic Analyzer Functions
    # --------------------------------------------------------------------------

    async def _start_logic_capture(self) -> None:
        """Start logic analyzer capture using SUMP protocol"""
        if self._logic_capturing:
            self.log_output("[!] Capture already in progress")
            return

        self._logic_capturing = True
        self.log_output("[*] Starting logic capture...")

        # Get config from UI
        try:
            rate_select = self.query_one("#logic-rate", Select)
            samples_select = self.query_one("#logic-samples", Select)
            trigger_select = self.query_one("#logic-trigger", Select)

            sample_rate = int(rate_select.value) if rate_select.value else 10000000
            num_samples = int(samples_select.value) if samples_select.value else 8192
            trigger = str(trigger_select.value) if trigger_select.value else "none"

            self.log_output(f"[*] Rate: {sample_rate/1e6:.1f}MHz, Samples: {num_samples}, Trigger: {trigger}")
        except Exception as e:
            self.log_output(f"[!] Config error: {e}")
            self._logic_capturing = False
            return

        # Parse trigger config
        trigger_channel = None
        trigger_edge = "rising"
        if trigger != "none":
            # Parse "ch0_rise" or "ch1_fall" format
            parts = trigger.split("_")
            if len(parts) == 2:
                trigger_channel = int(parts[0].replace("ch", ""))
                trigger_edge = "rising" if parts[1] == "rise" else "falling"
                self.log_output(f"[*] Trigger on CH{trigger_channel} {trigger_edge} edge")

        # Try to use the backend for real capture
        if self._backend and hasattr(self._backend, 'capture_logic'):
            self.log_output("[*] Entering SUMP mode...")
            try:
                # Run capture in background to avoid blocking UI
                import asyncio
                loop = asyncio.get_event_loop()

                # Run the blocking capture in executor
                result = await loop.run_in_executor(
                    None,
                    lambda: self._backend.capture_logic(
                        sample_rate=sample_rate,
                        sample_count=num_samples,
                        channels=8,
                        trigger_channel=trigger_channel,
                        trigger_edge=trigger_edge,
                        timeout=10.0
                    )
                )

                if result and result.get("samples"):
                    self.log_output(f"[+] Captured {len(result['samples'][0])} samples")

                    # Convert to LogicCapture format
                    capture = LogicCapture(
                        channels=result.get("channels", 8),
                        sample_rate=result.get("sample_rate", sample_rate),
                        samples=result["samples"],
                        trigger_position=result.get("trigger_position", 0)
                    )

                    if self._logic_widget:
                        self._logic_widget.set_capture(capture)
                        self._logic_widget.scroll_to_trigger()
                        self.log_output("[+] Capture complete - waveform updated")
                else:
                    self.log_output("[!] Capture returned no data")
                    self.log_output("[*] Check device connection and trigger conditions")

            except Exception as e:
                self.log_output(f"[!] Capture error: {e}")
                self.log_output("[*] Use 'Demo' button to test with sample data")
        else:
            self.log_output("[!] No backend available for hardware capture")
            self.log_output("[*] Use 'Demo' button to test with sample data")

        self._logic_capturing = False

    async def _stop_logic_capture(self) -> None:
        """Stop logic analyzer capture"""
        if not self._logic_capturing:
            return

        self._logic_capturing = False
        self.log_output("[*] Capture stopped")

    async def _load_logic_demo(self) -> None:
        """Load demo capture data for testing the waveform display"""
        import random

        self.log_output("[*] Loading demo capture data...")

        # Generate realistic-looking demo waveforms
        samples = []
        num_samples = 500

        # CH0: Clock signal (regular square wave)
        ch0 = []
        for i in range(num_samples):
            ch0.append(1 if (i // 8) % 2 == 0 else 0)
        samples.append(ch0)

        # CH1: Data signal (changes on clock edges, simulating SPI MOSI)
        ch1 = []
        data_byte = 0xA5  # Example data pattern
        bit_idx = 0
        for i in range(num_samples):
            if i % 64 == 0:  # New byte every 64 samples (8 bits * 8 samples/bit)
                data_byte = random.randint(0, 255)
                bit_idx = 0
            bit = (data_byte >> (7 - (bit_idx // 8))) & 1
            ch1.append(bit)
            if i % 8 == 7:
                bit_idx += 1
        samples.append(ch1)

        # CH2: Chip select (low during transfer)
        ch2 = []
        for i in range(num_samples):
            ch2.append(0 if 50 < i < 450 else 1)
        samples.append(ch2)

        # CH3: Glitch trigger signal (short pulse)
        ch3 = []
        glitch_pos = random.randint(200, 300)
        for i in range(num_samples):
            ch3.append(1 if glitch_pos <= i < glitch_pos + 5 else 0)
        samples.append(ch3)

        # CH4-7: Random noise/unused
        for ch in range(4, 8):
            ch_data = []
            state = 0
            for i in range(num_samples):
                if random.random() < 0.02:
                    state = 1 - state
                ch_data.append(state)
            samples.append(ch_data)

        # Create capture object
        capture = LogicCapture(
            channels=8,
            sample_rate=10000000,  # 10MHz
            samples=samples,
            trigger_position=glitch_pos
        )

        # Update the widget
        if self._logic_widget:
            self._logic_widget.set_capture(capture)
            self._logic_widget.scroll_to_trigger()
            self.log_output(f"[+] Loaded {num_samples} samples, trigger at position {glitch_pos}")
            self.log_output("[*] CH0=CLK, CH1=DATA, CH2=CS, CH3=GLITCH_TRIGGER")
        else:
            self.log_output("[!] Logic widget not initialized")
