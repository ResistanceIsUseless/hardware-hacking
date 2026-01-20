# hwh TUI Design Document

## Vision

Create a powerful, intuitive TUI that combines the best of glitch-o-bolt with multi-device coordination, intelligent automation, and seamless protocol handling.

## Core Principles

1. **Smart Device Management** - Auto-detect devices, remember configurations, allow manual override
2. **Multi-Device Workflows** - Coordinate multiple tools (e.g., Bolt glitching + Bus Pirate monitoring)
3. **Protocol Intelligence** - Context-aware automation based on protocol/responses
4. **Graceful Degradation** - Fall back to Bus Pirate native terminal when needed
5. **Non-Destructive** - Always allow escape to native tools without data loss

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     hwh TUI Main Screen                      │
├─────────────────────────────────────────────────────────────┤
│ Connected Devices:                                          │
│  [✓] Curious Bolt (/dev/ttyACM0) - Primary                 │
│  [✓] Bus Pirate v6 (/dev/ttyACM1) - Monitor                │
│  [ ] ST-Link v2 - Not connected                            │
│  [+] Add manual device...                                   │
│                                                             │
│ Active Workflow: UART Glitch Attack                         │
│  Device 1 (Bolt): Glitching @ boot                         │
│  Device 2 (BP):   Monitoring UART RX                       │
│                                                             │
│ Quick Actions:                                              │
│  [1] Device Management  [2] Protocol Analysis              │
│  [3] Glitch Campaign    [4] Flash Operations               │
│  [5] Multi-Device Sync  [6] Automation Scripts            │
│  [7] Native Terminal    [8] Settings                       │
│                                                             │
│ Status: Waiting for command...                             │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Device Architecture

### Device Pool Management

```python
class DevicePool:
    """
    Manages multiple hardware devices simultaneously.
    Handles device detection, configuration, and coordination.
    """

    devices: Dict[str, HardwareDevice]  # device_id -> device
    primary_device: Optional[str]       # Which device is "primary"
    device_roles: Dict[str, str]        # device_id -> role (e.g., "glitcher", "monitor")

    def detect_devices(self) -> List[DetectedDevice]:
        """Smart detection with automatic identification"""

    def assign_role(self, device_id: str, role: str):
        """Assign workflow role to device (glitcher, monitor, flasher)"""

    def coordinate(self, workflow: Workflow):
        """Coordinate multiple devices for a workflow"""
```

### Smart Device Selection

```python
class SmartDeviceSelector:
    """
    Intelligent device selection with memory and recommendations.
    """

    def __init__(self):
        self.history = DeviceHistory()  # Remember previous selections
        self.capabilities = CapabilityMatrix()

    def recommend_for_task(self, task: str) -> List[DeviceRecommendation]:
        """
        Recommend devices based on task requirements.

        Examples:
        - "glitch STM32" -> Curious Bolt (primary), ST-Link (verify)
        - "dump SPI flash" -> Shikra (fast), Bus Pirate (fallback)
        - "UART analysis" -> Bus Pirate (versatile), any UART-capable
        """

    def auto_select(self, task: str, available: List[Device]) -> DeviceSelection:
        """Automatically select best device(s) for task"""
```

## Multi-Device Workflows

### Example: Glitch + Monitor

```python
class GlitchMonitorWorkflow:
    """
    Use one device to glitch, another to monitor output.
    Classic use case: Bolt glitches, Bus Pirate monitors UART.
    """

    glitcher: Device  # Curious Bolt
    monitor: Device   # Bus Pirate on UART

    async def run(self):
        # Start monitoring in background
        monitor_task = asyncio.create_task(
            self.monitor.uart_capture(baudrate=115200)
        )

        # Run glitch campaign
        for offset in range(1000, 10000, 100):
            for width in range(10, 200, 10):
                # Trigger glitch
                await self.glitcher.glitch(offset, width)

                # Check monitor output
                output = await self.monitor.read_recent(timeout=0.1)

                if self.success_detected(output):
                    print(f"SUCCESS! offset={offset}, width={width}")
                    print(f"Output: {output}")
                    return True

        return False
```

### Example: Dual Monitoring

```python
class DualMonitorWorkflow:
    """
    Monitor multiple signals simultaneously.
    Use case: Bus Pirate on UART, Logic Analyzer on SPI.
    """

    uart_monitor: Device
    spi_monitor: Device

    async def run(self):
        # Monitor both simultaneously
        uart_task = asyncio.create_task(
            self.uart_monitor.capture()
        )
        spi_task = asyncio.create_task(
            self.spi_monitor.capture()
        )

        # Correlate events
        await self.correlate_captures(uart_task, spi_task)
```

## Protocol-Specific Automation

### UART Intelligence

```python
class UARTAutomation:
    """
    Smart UART automation based on responses.
    """

    def __init__(self, device: Device):
        self.device = device
        self.patterns = UARTPatternLibrary()

    async def auto_interact(self):
        """
        Automatically interact with UART based on what's detected.
        """

        # Read initial output
        output = await self.device.uart_read(timeout=2.0)

        # Detect what we're talking to
        if self.patterns.is_login_prompt(output):
            return await self.handle_login()
        elif self.patterns.is_shell(output):
            return await self.handle_shell()
        elif self.patterns.is_bootloader(output):
            return await self.handle_bootloader()
        elif self.patterns.is_custom_protocol(output):
            return await self.handle_custom()

    async def handle_shell(self):
        """
        Interacted with detected shell.
        """
        # Try common information gathering
        for cmd in ['uname -a', 'cat /proc/cpuinfo', 'id', 'ls -la /']:
            await self.device.uart_write(cmd + '\n')
            response = await self.device.uart_read(timeout=1.0)
            self.log_response(cmd, response)

        # Offer to run linpeas/enumeration
        if await self.prompt_user("Run enumeration script?"):
            await self.run_enumeration()

    async def handle_login(self):
        """
        Handle login prompt - try common credentials or brute force.
        """
        common_creds = [
            ('root', ''),
            ('root', 'root'),
            ('admin', 'admin'),
            ('user', 'user'),
        ]

        for username, password in common_creds:
            if await self.try_login(username, password):
                return True

        # Offer brute force
        if await self.prompt_user("Try password list?"):
            return await self.brute_force_login()
```

### I2C Intelligence

```python
class I2CAutomation:
    """
    Smart I2C scanning and interaction.
    """

    async def smart_scan(self):
        """
        Scan I2C bus and identify devices.
        """
        # Scan all addresses
        found_devices = []
        for addr in range(0x08, 0x78):  # Valid I2C range
            if await self.device.i2c_probe(addr):
                found_devices.append(addr)

        # Try to identify each device
        identified = []
        for addr in found_devices:
            device_info = await self.identify_device(addr)
            identified.append({
                'address': addr,
                'type': device_info.type,
                'confidence': device_info.confidence
            })

        return identified

    async def identify_device(self, addr: int):
        """
        Try to identify I2C device by reading common registers.
        """
        # Read register 0x00 (often device ID)
        try:
            reg_0 = await self.device.i2c_read_reg(addr, 0x00)

            # Check against known device IDs
            if reg_0 in I2C_DEVICE_DATABASE:
                return I2C_DEVICE_DATABASE[reg_0]
        except:
            pass

        return DeviceInfo(type='unknown', confidence=0.0)
```

### SPI Intelligence

```python
class SPIAutomation:
    """
    Smart SPI flash detection and operations.
    """

    async def detect_flash(self):
        """
        Detect SPI flash chip by reading JEDEC ID.
        """
        # Send JEDEC ID command (0x9F)
        jedec_id = await self.device.spi_transaction([0x9F, 0x00, 0x00, 0x00])

        manufacturer = jedec_id[1]
        device_type = jedec_id[2]
        capacity = jedec_id[3]

        chip_info = FLASH_DATABASE.lookup(manufacturer, device_type, capacity)
        return chip_info

    async def auto_dump(self):
        """
        Automatically detect and dump flash chip.
        """
        chip = await self.detect_flash()

        if chip:
            print(f"Detected: {chip.name} ({chip.size_mb}MB)")

            if await self.prompt_user(f"Dump {chip.name}?"):
                await self.dump_flash(chip)
```

## Bus Pirate Integration Strategy

### Option 1: Hybrid Mode (Recommended)

```python
class BusPirateIntegration:
    """
    Seamless switching between hwh TUI and native Bus Pirate terminal.
    """

    mode: str = "tui"  # or "native"

    def switch_to_native(self):
        """
        Drop into native Bus Pirate terminal.
        Preserves current configuration.
        """
        self.save_state()

        print("\n[Switching to native Bus Pirate terminal]")
        print("[Press Ctrl+] to return to hwh TUI]\n")

        # Pass through to native terminal
        self.device.enter_native_mode()

    def return_to_tui(self):
        """
        Return from native terminal back to TUI.
        """
        self.restore_state()
        print("\n[Returned to hwh TUI]")
```

### Option 2: Wrapper Commands

```python
class BusPirateWrapper:
    """
    Wrap common Bus Pirate commands for TUI use.
    Fall back to native terminal for advanced features.
    """

    # Implement most-used commands
    def voltage_probe(self):
        """Measure voltage on ADC pin"""

    def frequency_counter(self):
        """Frequency measurement"""

    def pwm_generator(self):
        """Generate PWM signal"""

    # For less-common features, offer native terminal
    def advanced_features(self):
        """Drop to native terminal for advanced features"""
        return self.integration.switch_to_native()
```

### Feature Priority Matrix

```
Priority 1 (Implement in TUI):
- Protocol communication (UART, SPI, I2C)
- Voltage measurement
- Pin configuration
- Flash operations
- Basic analysis

Priority 2 (Consider implementing):
- PWM generation
- Frequency measurement
- Logic analyzer capture
- Pull-up resistor control

Priority 3 (Use native terminal):
- Advanced protocol features
- Obscure bus modes
- Low-level bit-banging
- Debugging features
```

## TUI Layout Design

### Main Screen

```
┌─ hwh Hardware Hacking Toolkit ──────────────────────────────┐
│                                                              │
│ ┌─ Devices ────────────────────────────────────────────┐   │
│ │ [✓] Curious Bolt      /dev/ttyACM0   [Primary]       │   │
│ │     Role: Glitcher    Voltage: 3.3V   Status: Ready  │   │
│ │                                                       │   │
│ │ [✓] Bus Pirate v6     /dev/ttyACM1   [Monitor]       │   │
│ │     Role: UART Monitor  Baud: 115200  RX: Active     │   │
│ │                                                       │   │
│ │ [ ] ST-Link v2        Not connected                  │   │
│ │                                                       │   │
│ │ [+] Detect devices    [+] Add manual                 │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Active Workflow ────────────────────────────────────┐   │
│ │ RDP Bypass via Voltage Glitching                     │   │
│ │                                                       │   │
│ │ Progress: ████████░░░░░░░░░░ 45%                     │   │
│ │ Attempts: 4,500 / 10,000                             │   │
│ │ Success candidates: 3                                │   │
│ │                                                       │   │
│ │ [Pause] [Stop] [View Results]                        │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Output ─────────────────────────────────────────────┐   │
│ │ [Bus Pirate UART Monitor]                            │   │
│ │ Boot sequence detected...                            │   │
│ │ Trying glitch: offset=4200, width=85                 │   │
│ │ > Unusual response!                                  │   │
│ │ > Attempting flash read...                           │   │
│ │                                                       │   │
│ │ [Scroll: ↑↓] [Filter] [Export]                       │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                              │
│ Commands: [1] Workflows [2] Automation [3] Native [Q] Quit  │
└──────────────────────────────────────────────────────────────┘
```

### Workflow Selection Screen

```
┌─ Select Workflow ────────────────────────────────────────────┐
│                                                              │
│ Quick Start:                                                 │
│  [1] UART Password Bruteforce                               │
│  [2] Voltage Glitch Campaign                                │
│  [3] SPI Flash Dump                                         │
│  [4] I2C Device Scan                                        │
│  [5] Power Analysis                                         │
│                                                              │
│ Multi-Device:                                                │
│  [6] Glitch + Monitor (Bolt + Bus Pirate)                  │
│  [7] Dual Protocol Analysis                                 │
│  [8] Coordinated Attack                                     │
│                                                              │
│ Custom:                                                      │
│  [9] Build Custom Workflow                                  │
│  [0] Load Saved Workflow                                    │
│                                                              │
│ [ESC] Back                                                   │
└──────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. Device pool management
2. Multi-device coordination framework
3. Basic TUI with device selection
4. Workflow engine

### Phase 2: Protocol Automation
1. UART intelligence (shell detection, auto-interaction)
2. I2C scanning and identification
3. SPI flash detection
4. Protocol-specific helpers

### Phase 3: Bus Pirate Integration
1. Hybrid mode (TUI ↔ Native terminal)
2. Common command wrappers
3. State preservation
4. Hotkey switching

### Phase 4: Advanced Features
1. Workflow scripting/recording
2. Results database
3. ML-assisted parameter tuning
4. Integration with existing glitch-o-bolt campaigns

## Key Technical Decisions

### 1. TUI Library
**Recommendation:** Use `textual` (modern, async-friendly)
- Better than `urwid` (older, complex)
- Native async support for multi-device coordination
- Rich widgets and layouts
- Active development

### 2. Device Communication
**Keep current async architecture:**
- Each device has independent async task
- Coordination via asyncio primitives
- Non-blocking I/O throughout

### 3. State Management
**Use dataclasses + SQLite:**
- Device configurations → SQLite
- Workflow history → SQLite
- Session state → dataclasses in memory
- Export/import via JSON

### 4. Plugin Architecture
**For protocol automation:**
```python
class ProtocolPlugin:
    name: str
    protocols: List[str]  # ['uart', 'spi', etc.]

    async def auto_detect(self, device: Device) -> bool:
        """Can this plugin handle current situation?"""

    async def run_automation(self, device: Device) -> Results:
        """Execute automation"""
```

## Next Steps

1. **Review this design** with user
2. **Start with Phase 1** - basic multi-device TUI
3. **Prototype UART automation** - most commonly needed
4. **Add Bus Pirate hybrid mode** - critical for user adoption
5. **Iterate based on real usage**

---

*This design document will evolve as we build and test the system.*
