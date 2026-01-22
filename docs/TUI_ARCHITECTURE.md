# hwh TUI Architecture

## Overview

The hwh TUI is a multi-device hardware hacking interface built with [Textual](https://textual.textualize.io/). It supports simultaneous connections to multiple hardware devices, with each device getting its own dedicated tab.

## Design Philosophy

### Device-Based Tabs (NOT Protocol-Based)

**Wrong approach**: Tabs for SPI, I2C, UART, Glitch, Debug
**Correct approach**: Tabs for each connected device showing its capabilities

When you connect a device, a new tab is created:
- Tab label = Device name (e.g., "Bus Pirate 5", "Curious Bolt")
- Tab content = All features that device supports

### Why Device-Based?

1. **Real workflows**: Hardware hackers often use multiple tools simultaneously
   - Monitor UART on one device while glitching with another
   - View logic analyzer traces while sending SPI commands

2. **Device context**: Each device has different capabilities and configuration
   - Bus Pirate supports SPI, I2C, UART, Logic Analyzer
   - Curious Bolt focuses on glitching with triggers

3. **Simultaneous display**: Multiple device outputs visible at once

## Architecture

### File Structure

```
hwh/tui/
├── app.py                    # Main application
├── style.tcss                # Styling (glitch-o-bolt inspired)
├── layout_manager.py         # Split-screen layout handling
├── command_bar.py            # Smart command completion
└── panels/
    ├── __init__.py
    ├── base.py               # DevicePanel base class
    ├── buspirate.py          # Bus Pirate panel
    ├── bolt.py               # Curious Bolt panel
    ├── tigard.py             # Tigard panel
    ├── faultycat.py          # FaultyCat panel
    ├── tilink.py             # TI-Link/MSP-FET panel
    ├── blackmagic.py         # Black Magic Probe panel
    ├── uart_monitor.py       # Generic UART monitor
    └── logic_analyzer.py     # Logic analyzer widget
```

### Core Classes

#### DevicePanel (base.py)

Abstract base class for all device panels:

```python
class DevicePanel(Container, ABC):
    DEVICE_NAME: str = "Unknown Device"
    CAPABILITIES: List[PanelCapability] = []

    def __init__(self, device_info: DeviceInfo, app: HwhApp):
        self.device_info = device_info
        self.connected = False

    @abstractmethod
    def compose(self) -> ComposeResult:
        """Build the panel UI"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to device"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from device"""
        pass

    async def send_command(self, command: str) -> None:
        """Handle commands"""
        pass

    def get_command_suggestions(self, partial: str) -> List[CommandSuggestion]:
        """Auto-completion suggestions"""
        return []
```

#### HwhApp (app.py)

Main application class:

```python
class HwhApp(App):
    def __init__(self):
        self.available_devices: Dict[str, DeviceInfo] = {}
        self.connected_panels: Dict[str, DevicePanel] = {}

    async def connect_device(self, device_id: str) -> None:
        """Connect to device and create tab"""
        panel_class = self._get_panel_class(device_info)
        panel = panel_class(device_info, self)
        # Add tab, connect panel...

    async def disconnect_device(self, device_id: str) -> None:
        """Disconnect and remove tab"""
        pass
```

### Device Detection and Panel Selection

Devices are detected via USB VID:PID and matched to panel classes:

```python
DEVICE_PANELS = {
    (0x1209, 0x7331): BusPiratePanel,   # Bus Pirate 5/6
    (0xcafe, 0x4002): BoltPanel,         # Curious Bolt
    (0x0403, 0x6010): TigardPanel,       # Tigard
    (0x1d50, 0x6018): BlackMagicPanel,   # Black Magic Probe
    (0x0451, 0xbef3): TILinkPanel,       # TI MSP-FET
    # ... etc
}
```

Unknown devices default to UARTMonitorPanel.

## Adding New Devices

### 1. Create Panel Class

Create `hwh/tui/panels/mydevice.py`:

```python
from .base import DevicePanel, DeviceInfo, PanelCapability

class MyDevicePanel(DevicePanel):
    DEVICE_NAME = "My Device"
    CAPABILITIES = [PanelCapability.SPI, PanelCapability.UART]

    def compose(self) -> ComposeResult:
        # Build your UI
        with Vertical():
            yield Static("My Device Controls")
            yield Button("Do Thing", id="btn-thing")

    async def connect(self) -> bool:
        # Connect to hardware
        self.connected = True
        return True

    async def disconnect(self) -> None:
        self.connected = False
```

### 2. Register in app.py

Add VID:PID mapping:

```python
DEVICE_PANELS = {
    # ... existing devices ...
    (0x1234, 0x5678): MyDevicePanel,
}
```

### 3. Add to __init__.py

```python
from .mydevice import MyDevicePanel

__all__ = [
    # ... existing ...
    "MyDevicePanel",
]
```

## Supported Devices

| Device | Panel | Capabilities |
|--------|-------|--------------|
| Bus Pirate 5/6 | BusPiratePanel | SPI, I2C, UART, JTAG Scan, Logic |
| Curious Bolt | BoltPanel | Glitch, Logic, Power Analysis |
| Tigard | TigardPanel | SPI, I2C, UART, JTAG, SWD |
| FaultyCat | FaultyCatPanel | EMFI, Pin Detection |
| TI-Link (MSP-FET) | TILinkPanel | JTAG, SWD, EnergyTrace, BSL |
| Black Magic Probe | BlackMagicPanel | SWD, JTAG, GDB Server |
| Generic UART | UARTMonitorPanel | UART with regex filters |

## Styling

The TUI uses a color scheme inspired by glitch-o-bolt (Metagross Pokemon colors):

| Color | Hex | Usage |
|-------|-----|-------|
| Chinese Black | #141618 | Background |
| Police Blue | #2F596D | Borders, buttons |
| Crystal Blue | #5E99AE | Accents, active states |
| Pastel Blue | #9DC3CF | Text |
| Medium Carmine | #B13840 | Warnings, disconnected |
| Ash Gray | #B3B8BB | Secondary text |

## Target Resolution

- **Primary**: 1920 x 1200 px (MNT Reform Pocket 7" screen)
- **Minimum**: Supports smaller screens with responsive layout

## Key Bindings

| Key | Action |
|-----|--------|
| q | Quit |
| r | Refresh devices |
| d | Switch to Devices tab |
| ? | Show help |

## Multi-Device Workflows

### Example 1: Glitching with UART Monitoring

1. Connect to Curious Bolt (glitching device)
2. Connect to Bolt CTF (UART target)
3. Set up UART filters: "Boot", "Error", "Glitch"
4. Configure glitch parameters
5. Trigger glitch, watch UART for success indicators

### Example 2: Protocol Discovery with Bus Pirate

1. Connect to Bus Pirate
2. Switch to SPI mode
3. Read flash ID to identify chip
4. Dump flash contents
5. Switch to Logic Analyzer for signal analysis

### Example 3: Debug with Black Magic Probe

1. Connect to Black Magic Probe
2. Scan for SWD targets
3. Attach to target
4. Read memory / dump firmware
5. Set breakpoints, single step

## Future Enhancements

- Split-screen layouts (horizontal/vertical)
- Drag-and-drop panel arrangement
- Layout presets (save/load)
- Scripting API for automation
- Parameter sweep for glitch discovery
