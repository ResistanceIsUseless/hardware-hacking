# 🚀 START HERE - Bolt CTF Quick Start

## You Have Everything You Need!

✅ **Curious Bolt** detected on /dev/cu.usbmodem2103
✅ **Bolt CTF** detected on /dev/cu.usbserial-110
✅ **Bus Pirate** detected on /dev/cu.usbmodem6buspirate3
✅ **glitch-o-bolt** installed in `hwh/tooling/glitch-o-bolt/`
✅ **Bolt library** (scope.py) installed and working (v0.0.1)

## Step 1: Connect for Challenge 1 (RAM Dump)

**Do you have an ST-Link or any SWD debugger?**

If YES:
```
ST-Link → Bolt CTF:
  SWDIO → SWDIO
  SWCLK → SWCLK
  GND   → GND
  3.3V  → VMCU
```

Then run:
```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/hardware-hacking
python3 challenge1_ram_dump.py
```

## Step 2: Test Serial Output

Open a terminal and run:
```bash
tio /dev/cu.usbserial-110
```

You should see:
```
Hold one of the 4 challenge buttons to start them
```

**Press Button 1** on the Bolt CTF board. You should see Challenge 1 start!

## Step 3: Try glitch-o-bolt (The Amazing Auto-Glitcher)

**Location:**
```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh/tooling/glitch-o-bolt
```

**Available configs:**
```bash
ls Config*.py
```

**Test the TUI:**
```bash
python3 glitch-o-bolt.py
```

**What you'll see:**
```
┌────────────────────────────────────────┐
│  glitch-o-bolt v2.0                    │
│                                        │
│  UART Settings:                        │
│    port: /dev/ttyUSB0                  │
│    baud: 115200                        │
│                                        │
│  Glitch Settings:                      │
│    length:  [  0  ]                    │
│    repeat:  [  0  ]                    │
│    delay:   [  0  ]                    │
│                                        │
│  [Glitch Button] [Toggle]              │
│                                        │
│  Triggers:  [0-7 with switches]        │
│  Conditions: [Custom automation]       │
│                                        │
│  Main Window (Serial Output)           │
│  > Your UART commands here             │
└────────────────────────────────────────┘
```

**Controls:**
- Click buttons to adjust +/- values
- Type in inputs to set exact values
- Toggle switches to enable triggers
- "uart enable" switch connects serial
- "glitch" button sends single glitch
- "glitch toggle" runs continuous

## Step 4: Update Config for Your Serial Port

Edit the config file to match your setup:

```bash
# For Challenge 2:
nano ConfigChall02.py
```

Change:
```python
SERIAL_PORT = '/dev/ttyUSB0'  # ← Change this
```

To:
```python
SERIAL_PORT = '/dev/cu.usbserial-110'  # ← Your Bolt CTF port
```

## Step 5: Wire for Challenge 2 (Power Glitching)

**Minimum setup:**
```
Curious Bolt → Bolt CTF:
  GLITCH_OUT → VMCU (power pin)
  GND        → GND
```

**Advanced setup (auto-button-press):**
```
Curious Bolt → Bolt CTF:
  GLITCH_OUT → VMCU
  GPIO 0     → BTN2 (challenge 2 button)
  GND        → GND
```

## Step 6: Run Automated Challenge 2

```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/hardware-hacking/hwh/tooling/glitch-o-bolt

# Update serial port in config first!
nano ConfigChall02.py  # Change SERIAL_PORT = '/dev/cu.usbserial-110'

python3 glitch-o-bolt.py -c ConfigChall02.py
```

**Enable UART:**
1. Click "uart enable" switch (should turn green)
2. Watch serial output appear in main window

**What happens automatically:**
1. Detects "Hold one of the 4 challenge buttons" in serial output
2. Triggers GPIO 0 to press BTN2 (if wired)
3. Starts glitching with configured parameters
4. When "ctf" appears in output → stops glitching
5. **Flag displayed!** 🎉

## Keyboard Shortcuts in glitch-o-bolt

- **Tab**: Move between controls
- **Enter**: Activate buttons/submit inputs
- **Space**: Toggle switches
- **Ctrl+C**: Exit

## Test Your Curious Bolt Connection

```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/Projects/hardware-hacking

# Run quick test:
~/.pyenv/versions/3.12.10/bin/python3 -c "
from scope import Scope
s = Scope()
print(f'✅ Connected to Curious Bolt')
print(f'Testing glitch configuration...')
s.glitch.repeat = 42
s.glitch.ext_offset = 0
print(f'✅ Glitch configured: {s.glitch.repeat} cycles')
print(f'Ready to glitch!')
"
```

Expected output:
```
✅ Connected to Curious Bolt
Testing glitch configuration...
✅ Glitch configured: 42 cycles
Ready to glitch!
```

## Understanding the Automation

**ConfigChall02.py conditions:**
```python
conditions = [
    ["Flag", True,  "ctf", "stop_glitching"],           # Stop when flag found
    ["Chal2", True, "Hold one of", "start_chal_02"]     # Auto-start challenge
]
```

**What this means:**
- Pattern "Hold one of" in serial → calls `start_chal_02()`
- `start_chal_02()` pulses GPIO 0 high for 30ms → presses button
- Pattern "ctf" in serial → calls `stop_glitching()`
- **You don't need to do anything - it's fully automated!**

## Manual Testing (No Automation)

If you want to manually trigger glitches:

```bash
~/.pyenv/versions/3.12.10/bin/python3
```

```python
from scope import Scope

# Connect
s = Scope()

# Configure glitch
s.glitch.repeat = 42      # ~350ns glitch
s.glitch.ext_offset = 0   # No delay

# Single glitch
s.trigger()

# Sweep parameters
for width in range(10, 200, 5):
    s.glitch.repeat = width
    s.trigger()
    # Check serial output for flag
```

## Documentation

📖 **Full Guides:**
- `BOLT_CTF_WIRING_GUIDE.md` - Complete wiring diagrams
- `BOLT_CTF_QUICKSTART.md` - Step-by-step walkthrough
- `BOLT_CTF_GUIDE.md` - All 4 challenges explained
- `GLITCH_O_BOLT_ANALYSIS.md` - Design patterns analysis

📦 **Original Resources:**
- glitch-o-bolt tool: `hwh/tooling/glitch-o-bolt/`
- Bolt library: `~/hardware_hacking/tools/bolt/lib/scope.py`

## Troubleshooting

**"ModuleNotFoundError: No module named 'scope'"**
```bash
# Check installation:
~/.pyenv/versions/3.12.10/bin/python3 -c "import scope; print('OK')"

# If fails, reinstall:
cp ~/hardware_hacking/tools/bolt/lib/scope.py \
   ~/.pyenv/versions/3.12.10/lib/python3.12/site-packages/
```

**"ModuleNotFoundError: No module named 'textual'"**
```bash
~/.pyenv/versions/3.12.10/bin/pip install textual
```

**"Serial port permission denied"**
```bash
# macOS - no permissions needed
# Linux - add to dialout group:
sudo usermod -a -G dialout $USER
```

**"No serial output from Bolt CTF"**
```bash
# Verify device:
ls -la /dev/cu.usbserial-110

# If not found:
ls /dev/cu.*  # Find your device

# Test with tio:
tio /dev/cu.usbserial-110
```

## What's Next?

1. ✅ **Test serial output** - Verify Bolt CTF is responding
2. ✅ **Try glitch-o-bolt TUI** - Get familiar with interface
3. ✅ **Update config serial port** - Match your device
4. ✅ **Wire for Challenge 2** - GLITCH_OUT → VMCU, GND → GND
5. ✅ **Run automated campaign** - Watch the magic happen!

## You're Ready! 🚀

Everything is set up. The glitch-o-bolt tool is incredible - you're about to see fully automated hardware hacking in action.

**Pro tip:** Start with just the glitcher connected (no GPIO auto-button), manually press BTN2 on the board, and watch glitch-o-bolt automatically find the flag. Once that works, add the GPIO auto-trigger for full automation!

Good luck! 🔥
