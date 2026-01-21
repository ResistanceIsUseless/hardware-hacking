# TUI Redesign - Multi-Device Support

## What Changed

The hwh TUI has been completely redesigned to support multi-device workflows, inspired by glitch-o-bolt's excellent UI design.

### Before
- Single device selection only
- Large Connect/Disconnect buttons on main page
- No way to monitor multiple devices simultaneously
- Generic layout that didn't adapt to device capabilities

### After
- **Multi-device support**: Connect to multiple devices simultaneously
- **Device list sidebar**: Shows all detected devices with status indicators (● connected, ○ disconnected)
- **Per-device connection management**: Each device has its own Connect/Disconnect button
- **Adaptive glitch controls**: Glitch parameters only shown when a glitch-capable device is connected
- **UART filtering**: Regex pattern matching with highlighting for monitoring scenarios
- **glitch-o-bolt styling**: Clean, professional color scheme and layout

## Key Features

### 1. Multi-Device Connection
```
Device List:
● Bus Pirate 5 (1209:7331)     [Disconnect]
○ Curious Bolt (cafe:4002)     [Connect]
○ Bolt CTF (cafe:4004)         [Connect]
```

You can now:
- Connect to Bolt CTF to monitor UART
- Connect to Curious Bolt to perform glitching
- See outputs from both devices simultaneously

### 2. Glitch Controls (from glitch-o-bolt)
When a glitch-capable device is connected, the sidebar shows:

```
┌─ glitch parameters ────────────────┐
│ length:  [-100][-10][-1][  0  ]save[+1][+10][+100] │
│ repeat:  [-100][-10][-1][  0  ]save[+1][+10][+100] │
│ delay:   [-100][-10][-1][  0  ]save[+1][+10][+100] │
│                                                      │
│ [  glitch  ]                                         │
│ [ ] continuous                                       │
│                                                      │
│ ┌─ status ──────────┐                               │
│ │ length:     0     │                               │
│ │ repeat:     0     │                               │
│ │ delay:      0     │                               │
│ │ elapsed: 00:00:00 │                               │
│ └───────────────────┘                               │
└──────────────────────────────────────────────────────┘
```

### 3. UART Filtering
The UART tab now includes regex filter support:

```
┌─ filters ─────────────────┐
│ Regex patterns:            │
│                            │
│ [Boot successful   ] [X]   │
│ [Error:.*          ] [X]   │
│ [Glitch.*          ] [X]   │
│                            │
│ [regex pattern...  ] [Add] │
└────────────────────────────┘
```

Perfect for scenarios like:
- Monitor "Boot" to see when target resets
- Highlight "Error" messages in red
- Watch for "Glitch" success indicators

### 4. Clean Color Scheme
Inspired by glitch-o-bolt's Metagross Pokemon color scheme:
- **Background**: #141618 (Chinese Black)
- **Borders**: #2F596D (Police Blue)
- **Text**: #9DC3CF (Pastel Blue)
- **Accents**: #5E99AE (Crystal Blue)
- **Status/Error**: #B13840 (Medium Carmine)
- **Secondary**: #B3B8BB (Ash Gray)

## File Structure

```
hwh/tui/
├── app.py          # Main TUI application (redesigned)
├── style.tcss      # glitch-o-bolt inspired styling (new)
└── REDESIGN.md     # This file
```

## Implementation Details

### Device Connection Management
Each device gets its own `DeviceConnection` object:
```python
class DeviceConnection:
    def __init__(self, device: DeviceInfo, backend: Backend):
        self.device = device
        self.backend = backend
        self.connected = False
        self.uart_buffer = ""
```

The app maintains:
- `available_devices`: All detected devices
- `connections`: Currently connected devices
- `selected_device`: Active glitch device (if any)

### Glitch Parameter Control
Increment/decrement buttons modify values:
```python
async def handle_param_adjust(self, button_id: str):
    # Parse button_id like "length+10" or "repeat-100"
    param_name, adjustment = parse_button_id(button_id)
    new_value = max(0, current_value + adjustment)

    # Update input widget
    # Update status table
    # Store in self.glitch_*
```

### UART Filtering
Regex patterns can highlight specific output:
```python
@dataclass
class UartFilter:
    pattern: str
    color: str
    enabled: bool = True

# When data arrives:
for filter in self.uart_filters:
    if re.search(filter.pattern, uart_output):
        # Apply highlighting
```

## Usage Examples

### Example 1: Basic Glitching
```
1. Launch: hwh tui
2. Connect to Curious Bolt (click [Connect] in device list)
3. Glitch controls appear automatically
4. Set length: 350, repeat: 1000, delay: 0
5. Click [glitch] button or toggle continuous mode
```

### Example 2: Multi-Device Monitoring
```
1. Launch: hwh tui
2. Connect to Bolt CTF (for UART monitoring)
3. Connect to Curious Bolt (for glitching)
4. Go to UART tab
5. Add filter: "Boot.*" to highlight boot messages
6. Add filter: "Error.*" to highlight errors
7. Return to Console tab
8. Trigger glitch - see results from both devices
```

### Example 3: SPI Flash Dumping
```
1. Launch: hwh tui
2. Connect to Bus Pirate or Tigard
3. Go to SPI tab
4. Configure speed: 1000000
5. Click [Read Flash ID]
6. Click [Dump Flash]
7. Monitor progress in Console tab
```

## Testing

To test the new TUI:
```bash
cd /Users/mgriffiths/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/Code/hardware-hacking

# Run from source
PYTHONPATH=. python3 -m hwh.tui.app

# Or via cli
python3 -m hwh tui
```

With your hardware setup:
- Bus Pirate 5/6 should appear as available device
- Curious Bolt should appear as available device
- Bolt CTF should appear as available device
- Connect to multiple simultaneously to test multi-device support

## Still TODO

1. **Async UART reading**: Background tasks to read serial data from all connected devices
2. **Continuous glitching**: When switch is enabled, continuously trigger glitches
3. **Trigger configuration**: Add 8 trigger switches with ^/v/- symbols (like glitch-o-bolt)
4. **Conditions monitoring**: Automated responses to UART patterns
5. **Filter display**: Show active filters in UART tab with enable/disable toggles
6. **Parameter sweep**: Automated parameter sweeping for glitch discovery
7. **Session persistence**: Save/load device configurations

## Design Philosophy

The new TUI follows these principles:

1. **Multi-device first**: Support multiple simultaneous connections from the ground up
2. **Adaptive UI**: Show only relevant controls based on connected device capabilities
3. **Professional appearance**: Clean, consistent styling inspired by successful tools
4. **Workflow-oriented**: Designed for real attack scenarios (monitor + glitch, etc.)
5. **Regex filtering**: Powerful pattern matching for complex monitoring needs

## Credits

- TUI framework: [Textual](https://textual.textualize.io/)
- Design inspiration: [glitch-o-bolt](https://github.com/0xRoM/glitch-o-bolt) by 0xRoM
- Color scheme: Metagross Pokemon colors from schemecolor.com

## Next Steps

1. Test with actual hardware (Bus Pirate, Bolt, Bolt CTF)
2. Implement async UART reading for all connected devices
3. Add trigger configuration UI
4. Implement continuous glitching mode
5. Add filter management UI in UART tab
6. Consider adding logging/session recording
