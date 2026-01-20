# glitch-o-bolt Design Analysis

**Credit**: Original tool by 0xRoM (https://rossmarks.uk/git/0xRoM/glitch-o-bolt)

## Overview

glitch-o-bolt is an exceptional TUI (Terminal User Interface) tool for voltage glitching automation with the Curious Bolt. It represents best-in-class design for hardware hacking automation.

## Key Design Patterns Worth Adopting

### 1. **Config-Driven Architecture**

Instead of hardcoding logic, glitch-o-bolt uses Python config files that define:
- Initial glitch parameters (LENGTH, REPEAT, DELAY)
- Trigger configurations (pull-up/pull-down for 8 GPIO pins)
- **Conditions**: Pattern matching in serial output with associated actions
- **Custom functions**: User-defined automation logic

**Example from ConfigChall02.py:**
```python
conditions = [
    ["Flag", True,  "ctf", "stop_glitching"],
    ["Chal2", True, "Hold one of", "start_chal_02"]
]

def stop_glitching():
    elapsed = functions.get_glitch_elapsed()
    functions.glitching_switch(False)
    functions.add_text(f"[auto] glitching stopped (elapsed: {elapsed})")

def start_chal_02():
    functions.run_output_high(0, 30000000)  # Trigger challenge button via GPIO
```

**Why This Is Brilliant:**
- Zero code changes needed for different targets
- Conditions enable fully automated glitching campaigns
- Custom functions can trigger GPIO, modify parameters, or stop on success
- Shareable configs = shareable attack methodologies

### 2. **Condition-Based Automation**

The `conditions` system is the killer feature:

**Structure:** `["Name", enabled, "search_pattern", "function_name"]`

**How It Works:**
- Serial output continuously buffered in background
- Buffer scanned for pattern matches every 100ms
- When pattern found + condition enabled → execute function
- Functions can modify glitch params, trigger GPIOs, stop glitching, etc.

**ConfigGlitchBrute.py Example:**
```python
conditions = [
    ["Flag", True,  "ctf", "stop_glitching"],                    # Success detector
    ["pt1", True, "Hold one of", "start_chal_02"],               # Challenge started
    ["pt2", True, "Starting challenge 2", "glitched_too_far"],   # Overshot detector
    ["std", True, "1000000", "perform_glitch"]                   # Standard output = next iteration
]

def perform_glitch():
    """Automated parameter sweep with adaptive step sizes"""
    # Increment delay → length → repeat in sequence
    # Automatically refine parameters when "glitched_too_far" detected
```

**This enables:**
- Fully automated brute-force parameter sweeps
- Adaptive refinement (coarse → fine tuning)
- Success detection without human monitoring
- Multi-stage attack chains (e.g., trigger button → wait for output → glitch → detect success)

### 3. **Textual TUI Architecture**

Uses the `textual` library for a professional, reactive interface:

**Benefits:**
- Real-time serial monitoring in main window
- Interactive controls (buttons, switches, inputs)
- Status display updates live during glitching
- Scrollable log with proper line handling
- Works over SSH (no GUI needed)

**Key Widgets:**
- **Log widget**: Scrollable serial output with auto-scroll
- **DataTable**: Live glitch parameter display
- **Switches**: Toggle triggers, conditions, logging
- **Grid layout**: Organized 8-trigger interface
- **Input field**: Send UART commands during glitching

### 4. **Multi-Threaded Serial + Async Design**

**Architecture:**
```python
async def on_ready():
    asyncio.create_task(self.connect_serial())      # Serial connection manager
    asyncio.create_task(functions.monitor_buffer())  # Condition checker
    asyncio.create_task(functions.glitch())          # Glitch engine
```

**Smart Serial Handling:**
- Non-blocking reads with `asyncio.get_event_loop().run_in_executor()`
- Separate buffer for condition monitoring vs display
- Thread-safe buffer with `asyncio.Lock()`
- Preserves original line endings (critical for parsing)
- Auto-reconnect on serial errors

**Why This Matters:**
- UI remains responsive during glitching
- Serial monitoring doesn't block glitch triggering
- Condition checks run independently of display updates
- Proper error handling prevents crashes

### 5. **GPIO Control Integration**

**Trigger System:**
```python
triggers = [
    ['-', False],  # Pin 0: disabled
    ['^', True],   # Pin 1: pull-up enabled
    ['v', True],   # Pin 2: pull-down enabled
    # ... 8 pins total
]
```

**Functions Available:**
- `run_output_high(pin, duration_ns)` - Pulse GPIO high
- `run_output_low(pin, duration_ns)` - Pulse GPIO low
- `set_triggers()` - Apply pull-up/pull-down configuration

**Use Cases:**
- Auto-press challenge buttons via GPIO
- Trigger external equipment
- Provide clock signals
- Control power switches

### 6. **Incremental Parameter Sweeping**

**ConfigGlitchBrute.py implements smart sweeping:**

```python
# Start with coarse increments (100)
inc_delay_amount = 100
inc_repeat_amount = 100
inc_length_amount = 100

def perform_glitch():
    # Cycle through delay → length → repeat
    # Each successful iteration increments by current amount

def glitched_too_far():
    # Detected we overshot (e.g., "Starting challenge 2" appeared)
    # Decrement last value and reduce step size: 100 → 10 → 1
```

**This creates adaptive refinement:**
1. Broad sweep finds approximate range (steps of 100)
2. Overshoot detected → backtrack and reduce step size
3. Fine-tune with steps of 10, then 1
4. Automatically converges on working parameters

### 7. **Modular Function System**

**functions.py provides reusable building blocks:**
- `start_glitch(length, repeat, delay)` - Execute single glitch
- `get_glitch_elapsed()` - Timing for statistics
- `add_text(message)` - Output to main window
- `log_message(message)` - Debug logging
- `send_uart_message(text)` - Send commands
- `write_to_log(data, timestamp)` - File logging

**Benefits:**
- Config files stay simple
- Common operations standardized
- Easy to extend with new functions
- Debugging infrastructure built-in

### 8. **FaultyCat Integration** (Future Enhancement)

The tool already has hooks for FaultyCat support:

```python
from FaultycatModules import Worker

faulty_worker = Worker.FaultyWorker()
```

This shows forward-thinking design for multi-tool support.

## Patterns to Integrate into hwh Package

### Immediate Wins:

1. **Config File System**
   - Add `hwh/configs/` directory
   - Define standard config format
   - Enable `hwh glitch --config challenge2.py`

2. **Condition Engine**
   - Create `hwh.conditions` module
   - Serial buffer + pattern matching
   - Action dispatcher

3. **CLI Enhancements**
   - `hwh glitch sweep --width-min X --width-max Y --step Z`
   - `hwh glitch auto --config file.py` (run conditions)
   - `hwh monitor --pattern "ctf" --action stop`

4. **TUI Mode**
   - `hwh tui` - Launch textual interface
   - Real-time parameter adjustment
   - Live serial monitoring
   - Success detection

### Architecture Integration:

```python
# hwh/glitch_engine.py
class GlitchCampaign:
    def __init__(self, backend, config):
        self.backend = backend
        self.config = config
        self.conditions = ConditionMonitor(config.conditions)

    async def run(self):
        """Execute automated glitch campaign with condition monitoring"""

# hwh/conditions.py
class ConditionMonitor:
    def __init__(self, conditions):
        self.conditions = conditions  # List of (name, enabled, pattern, action)
        self.buffer = ""

    def check(self, new_data):
        """Check for pattern matches and trigger actions"""
```

## Key Takeaways

**What makes glitch-o-bolt excellent:**

1. ✅ **Fully automated** - Set config, walk away, get flag
2. ✅ **Highly configurable** - No code changes for new targets
3. ✅ **Pattern-based** - Success detection via serial output
4. ✅ **Adaptive** - Auto-refines parameters on overshoot
5. ✅ **Professional UX** - Clean TUI, real-time updates
6. ✅ **Extensible** - Custom functions for any automation need
7. ✅ **Multi-device ready** - Bolt + FaultyCat hooks
8. ✅ **Robust** - Error handling, auto-reconnect, logging

**Design philosophy:**
> "Make the common case trivial, and the complex case possible"

Running a CTF challenge should be as simple as:
```bash
python3 glitch-o-bolt.py -c ConfigChall02.py
# Walk away, flag appears automatically
```

This is the gold standard for hardware hacking automation.

## Wiring Setup for Bolt CTF

Based on the configs, here's the physical setup:

### Challenge 2 (Power Glitching):

```
Curious Bolt → Bolt CTF:
  GLITCH_OUT → VCC (insert in power path)
  GPIO 0 → Challenge 2 button (auto-trigger)
  GND → GND

Serial Monitor:
  Bolt CTF TX → Bolt RX (pin 0 or USB-serial adapter)
  GND → GND
```

### Challenge 3/4:

Similar setup with different GPIO mappings in the config.

## Next Steps for Integration

1. Create `hwh/tui/` module using textual
2. Add `ConditionMonitor` to `GlitchBackend` base class
3. Implement config file loader
4. Port key functions to `backend_bolt.py`
5. Add `hwh tui` command to CLI
6. Create example configs for common targets

**Credit**: All design patterns documented here are from the original glitch-o-bolt tool by 0xRoM.
