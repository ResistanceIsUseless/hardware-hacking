# Comprehensive Hardware Hacking Setup Guide v3
## macOS (M-series) and ARM Linux Configuration
## With AI-Assisted Tools & MCP Integrations

### Overview
This guide covers complete software installation for a hardware hacking lab focused on IoT/embedded security testing, firmware analysis, and fault injection. It includes setup for your primary hardware kit plus AI-powered reverse engineering tools.

---

## Your Hardware Kit

| Tool | Primary Role | Price |
|------|-------------|-------|
| **Bus Pirate v5/v6** | Protocol interface (UART, SPI, I2C, JTAG) | ~$60 |
| **GreatFET One** | USB security (emulation, MITM, fuzzing) | ~$120 |
| **Curious Bolt** | Voltage glitching + power analysis + logic analyzer | ~$150 |
| **Faulty Cat v2.1** | EMFI + voltage glitch + SWD/JTAG detection | ~$100 |
| **Shikra** | Fast SPI flash dumps, JTAG, UART | ~$45 |
| **Total** | Comprehensive hardware hacking lab | **~$475** |

---

## Part 1: System Prerequisites

### 1.1 macOS Requirements
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Xcode Command Line Tools
xcode-select --install

# Install Python 3 and package managers
brew install python@3.11 pipx
pipx ensurepath

# Install essential build tools
brew install git cmake ninja
brew install libusb libftdi

# Serial/USB tools
brew install screen minicom tio
```

### 1.2 ARM Linux Requirements
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y pipx
pipx ensurepath

# Install build essentials
sudo apt install -y build-essential git cmake ninja-build
sudo apt install -y libusb-1.0-0-dev libftdi1-dev

# Serial/USB tools
sudo apt install -y screen minicom picocom tio
sudo apt install -y usbutils

# Additional dependencies
sudo apt install -y libncurses5-dev libncursesw5-dev
sudo apt install -y libreadline-dev libssl-dev
```

### 1.3 USB Permissions (Linux Only)

Create comprehensive udev rules:

```bash
sudo nano /etc/udev/rules.d/99-hardware-hacking.rules
```

Add the following:
```
# =============================================================
# HARDWARE HACKING UDEV RULES
# =============================================================

# Bus Pirate v5/v6
SUBSYSTEM=="usb", ATTR{idVendor}=="1209", ATTR{idProduct}=="7331", MODE="0666", GROUP="plugdev"

# GreatFET One
SUBSYSTEM=="usb", ATTR{idVendor}=="1d50", ATTR{idProduct}=="60e6", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="1fc9", ATTR{idProduct}=="000c", MODE="0666", GROUP="plugdev"

# Curious Bolt (RP2040-based)
SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", MODE="0666", GROUP="plugdev"

# Electronic Cats Faulty Cat (RP2040-based)
SUBSYSTEM=="usb", ATTR{idVendor}=="1209", ATTR{idProduct}=="50b0", MODE="0666", GROUP="plugdev"

# Shikra/FTDI devices
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", MODE="0666", GROUP="plugdev"

# ChipWhisperer
SUBSYSTEM=="usb", ATTR{idVendor}=="2b3e", MODE="0666", GROUP="plugdev"
KERNEL=="ttyACM*", ATTRS{idVendor}=="2b3e", MODE="0666", GROUP="plugdev"

# Flipper Zero
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="5740", MODE="0666", GROUP="plugdev"

# Proxmark3
SUBSYSTEM=="usb", ATTR{idVendor}=="9ac4", ATTR{idProduct}=="4b8f", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="2d2d", ATTR{idProduct}=="504d", MODE="0666", GROUP="plugdev"

# HackRF One
SUBSYSTEM=="usb", ATTR{idVendor}=="1d50", ATTR{idProduct}=="6089", MODE="0666", GROUP="plugdev"

# Saleae Logic Analyzers
SUBSYSTEM=="usb", ATTR{idVendor}=="0925", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="21a9", MODE="0666", GROUP="plugdev"

# Generic USB serial converters
SUBSYSTEM=="tty", ATTRS{idVendor}=="1209", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="plugdev"
```

Apply rules:
```bash
sudo usermod -a -G plugdev,dialout $USER
sudo udevadm control --reload-rules
sudo udevadm trigger
# Log out and back in for changes to take effect
```

---

## Part 2: Bus Pirate v5/v6 Setup

### 2.1 Software Installation

**Both macOS and Linux:**
```bash
# Install Python libraries
pip3 install --user pyBusPirateLite pyserial

# Clone firmware repo (for reference/updates)
mkdir -p ~/hardware_hacking/tools/buspirate
cd ~/hardware_hacking/tools/buspirate
git clone https://github.com/DangerousPrototypes/BusPirate5-firmware.git
```

### 2.2 Install flashrom (for SPI flash operations)

**macOS:**
```bash
brew install flashrom
```

**Linux:**
```bash
sudo apt install -y flashrom

# Or build from source for latest features
git clone https://github.com/flashrom/flashrom.git
cd flashrom
make
sudo make install
```

### 2.3 Connect and Test

```bash
# Find device
# macOS:
ls /dev/tty.usbmodem* /dev/cu.usbmodem*

# Linux:
ls /dev/ttyACM* /dev/ttyUSB*

# Connect via tio (recommended) or screen
tio /dev/ttyACM0
# Or
screen /dev/ttyACM0 115200

# Bus Pirate commands
i          # Display device info
m          # Select mode menu
~          # Self-test
```

### 2.4 Flashrom with Bus Pirate

```bash
# Enter binary mode on Bus Pirate first:
# In Bus Pirate terminal: binmode -> select "Legacy Binary Mode for Flashrom"

# Read SPI flash
flashrom -p buspirate_spi:dev=/dev/ttyACM0,spispeed=1M -r firmware_dump.bin

# Write SPI flash
flashrom -p buspirate_spi:dev=/dev/ttyACM0,spispeed=1M -w new_firmware.bin

# Identify chip only
flashrom -p buspirate_spi:dev=/dev/ttyACM0 -V
```

---

## Part 3: GreatFET One Setup

### 3.1 Install GreatFET Software

**Both macOS and Linux:**
```bash
# Install GreatFET host tools
pip3 install --user greatfet

# Or use pipx for isolation
pipx install greatfet

# Install FaceDancer for USB emulation
pip3 install --user facedancer
# Or
pipx install facedancer
```

**Linux-specific udev rules:**
```bash
# If not already in main rules file
sudo wget https://raw.githubusercontent.com/greatscottgadgets/greatfet/master/host/util/54-greatfet.rules \
    -O /etc/udev/rules.d/54-greatfet.rules
sudo udevadm control --reload-rules
```

### 3.2 Update GreatFET Firmware

```bash
# Check device connection
greatfet info
# Or shorter:
gf info

# Update firmware to latest
greatfet_firmware --auto
```

### 3.3 FaceDancer USB Emulation Setup

```bash
# Set environment variable for GreatFET backend
export BACKEND=greatfet

# Add to shell profile (~/.bashrc or ~/.zshrc)
echo 'export BACKEND=greatfet' >> ~/.bashrc

# Test FaceDancer installation
python3 -c "import facedancer; print('FaceDancer ready')"
```

### 3.4 Example: USB Keyboard Emulation

```python
#!/usr/bin/env python3
# Save as: usb_keyboard_test.py

from facedancer import main
from facedancer.devices.keyboard import USBKeyboardDevice

# Create and run USB keyboard emulator
keyboard = USBKeyboardDevice()
main(keyboard)
```

### 3.5 USB MITM Setup

```python
#!/usr/bin/env python3
# Save as: usb_mitm_example.py

from facedancer import main
from facedancer.proxy import USBProxyDevice

# Requires two USB ports on GreatFET
# Connect target device to USB1, host to USB0
proxy = USBProxyDevice(idVendor=0x1234, idProduct=0x5678)
main(proxy)
```

---

## Part 4: Curious Bolt Setup

The Curious Bolt is an all-in-one hardware security tool with:
- Crowbar voltage glitcher (8.3ns resolution)
- Differential power scope (35MSPS)
- 8-channel logic analyzer (PulseView compatible)

### 4.1 Install Software Dependencies

**Both macOS and Linux:**
```bash
# Install Python libraries
pip3 install --user pyserial numpy matplotlib

# Install PulseView for logic analysis
# macOS:
brew install --cask pulseview

# Linux:
sudo apt install -y sigrok pulseview
```

### 4.2 Clone Curious Bolt Resources

```bash
mkdir -p ~/hardware_hacking/tools/curious_bolt
cd ~/hardware_hacking/tools/curious_bolt

# Clone official resources (check Curious Supplies GitHub)
git clone https://github.com/curious-supplies/bolt-examples.git

# The Bolt includes the ECSC23 target board with 4 challenges
```

### 4.3 Basic Glitching Setup

```python
#!/usr/bin/env python3
# curious_bolt_glitch.py - Basic voltage glitching example

import serial
import time

# Connect to Curious Bolt
ser = serial.Serial('/dev/ttyACM0', 115200)

def configure_glitch(delay_ns, width_ns):
    """Configure glitch parameters"""
    # Commands depend on Curious Bolt firmware
    # Check documentation for exact protocol
    ser.write(f"GLITCH_DELAY {delay_ns}\n".encode())
    ser.write(f"GLITCH_WIDTH {width_ns}\n".encode())

def trigger_glitch():
    """Trigger a single glitch"""
    ser.write(b"GLITCH_TRIGGER\n")

def arm_glitch():
    """Arm glitch to trigger on external signal"""
    ser.write(b"GLITCH_ARM\n")

# Example usage
configure_glitch(delay_ns=1000, width_ns=50)
trigger_glitch()
```

### 4.4 Logic Analyzer with PulseView

```bash
# Start PulseView
pulseview

# In PulseView:
# 1. Select "fx2lafw" or appropriate driver
# 2. Connect to Curious Bolt logic analyzer port
# 3. Configure sample rate and channels
# 4. Add protocol decoders (SPI, I2C, UART, etc.)
```

---

## Part 5: Faulty Cat v2.1 Setup

Electronic Cats Faulty Cat combines:
- Electromagnetic Fault Injection (EMFI) ~250V, 0.2W
- Voltage glitching capability
- SWD/JTAG pin detection (like JTAGulator)

### 5.1 Install Software

**Both macOS and Linux:**
```bash
# Install Python dependencies
pip3 install --user pyserial

# Clone Electronic Cats repositories
mkdir -p ~/hardware_hacking/tools/faulty_cat
cd ~/hardware_hacking/tools/faulty_cat
git clone https://github.com/ElectronicCats/faultycat.git
```

### 5.2 Arduino IDE Setup (for firmware updates)

**macOS:**
```bash
brew install --cask arduino-ide
```

**Linux:**
```bash
# Download Arduino IDE
wget https://downloads.arduino.cc/arduino-ide/arduino-ide_latest_Linux_ARM64.AppImage
chmod +x arduino-ide_latest_Linux_ARM64.AppImage
# Or use flatpak/snap
```

**Configure Arduino for Electronic Cats boards:**
1. Open Arduino IDE → Preferences
2. Add Board Manager URL:
   ```
   https://electroniccats.github.io/Arduino_Boards_Index/package_electroniccats_index.json
   ```
3. Tools → Board Manager → Search "Electronic Cats" → Install

### 5.3 Basic EMFI Attack Script

```python
#!/usr/bin/env python3
# faulty_cat_emfi.py - Basic EMFI attack example

import serial
import time

class FaultyCat:
    def __init__(self, port='/dev/ttyACM0'):
        self.ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)  # Wait for device reset
        
    def arm(self):
        """Arm the EMFI pulse generator"""
        self.ser.write(b'ARM\n')
        response = self.ser.readline()
        return response
        
    def pulse(self):
        """Trigger EMFI pulse"""
        self.ser.write(b'PULSE\n')
        response = self.ser.readline()
        return response
        
    def set_power(self, level):
        """Set pulse power level"""
        self.ser.write(f'POWER {level}\n'.encode())
        response = self.ser.readline()
        return response
        
    def detect_swd(self):
        """Run SWD/JTAG pin detection"""
        self.ser.write(b'DETECT\n')
        # Read multi-line response
        lines = []
        while True:
            line = self.ser.readline()
            if not line:
                break
            lines.append(line.decode().strip())
        return lines

# Example usage
fc = FaultyCat()
fc.arm()
time.sleep(0.5)
fc.pulse()
```

### 5.4 SWD/JTAG Detection

```python
#!/usr/bin/env python3
# Pin detection similar to JTAGulator

from faulty_cat_emfi import FaultyCat

fc = FaultyCat()

# Connect target pins to Faulty Cat GPIO
# Run detection
results = fc.detect_swd()
for line in results:
    print(line)

# Output will show detected debug interfaces and pin mappings
```

---

## Part 6: Shikra Setup (Fast SPI/JTAG)

Shikra uses the FT232H chip for high-speed SPI flash dumping.

### 6.1 Install FTDI Drivers and Tools

**macOS:**
```bash
# Install libftdi
brew install libftdi

# Install flashrom (already done above)
brew install flashrom
```

**Linux:**
```bash
sudo apt install -y libftdi1-dev ftdi-eeprom

# Build flashrom with FT2232 support (already installed)
```

### 6.2 Flashrom with Shikra

```bash
# Identify flash chip
flashrom -p ft2232_spi:type=232H -V

# Read entire flash (much faster than Bus Pirate!)
flashrom -p ft2232_spi:type=232H -r firmware_dump.bin

# Write new firmware
flashrom -p ft2232_spi:type=232H -w new_firmware.bin

# Verify after write
flashrom -p ft2232_spi:type=232H -v firmware_dump.bin
```

### 6.3 Speed Comparison

| Tool | 4MB Flash Read Time |
|------|---------------------|
| Bus Pirate | ~30-45 minutes |
| Shikra | ~3-5 minutes |
| Tigard | ~3-5 minutes |
| CH341A | ~2-3 minutes |

---

## Part 7: Firmware Analysis Tools

### 7.1 Binwalk Installation

**macOS:**
```bash
pip3 install --user binwalk

# Install extraction dependencies
brew install p7zip squashfs
```

**Linux:**
```bash
pip3 install --user binwalk

# Install all extraction dependencies
sudo apt install -y squashfs-tools cramfsswap sasquatch \
    jefferson ubi_reader p7zip-full unzip arj lha lrzip
```

### 7.2 Ghidra Installation

**Both platforms:**
```bash
# Download Ghidra from NSA GitHub
# https://github.com/NationalSecurityAgency/ghidra/releases

# macOS:
brew install --cask ghidra

# Or manual install:
wget https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.2_build/ghidra_11.2_PUBLIC_20241105.zip
unzip ghidra_11.2_PUBLIC_20241105.zip
mv ghidra_11.2_PUBLIC ~/ghidra

# Add to PATH
echo 'export GHIDRA_HOME="$HOME/ghidra"' >> ~/.bashrc
echo 'export PATH="$PATH:$GHIDRA_HOME"' >> ~/.bashrc
```

**Install Java (required for Ghidra):**
```bash
# macOS:
brew install openjdk@17
sudo ln -sfn $(brew --prefix)/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk

# Linux:
sudo apt install -y openjdk-17-jdk
```

### 7.3 Radare2 Installation

```bash
# macOS:
brew install radare2

# Linux:
git clone https://github.com/radareorg/radare2
cd radare2
sys/install.sh

# Install r2pipe for Python scripting
pip3 install --user r2pipe
```

### 7.4 EMBA Firmware Analyzer

EMBA is the comprehensive open-source firmware security analyzer with AI support.

```bash
# Clone EMBA
git clone https://github.com/e-m-b-a/emba.git
cd emba

# Install (requires Docker)
./installer.sh -d  # Default installation

# Or full installation with all extras
./installer.sh -F

# Run basic firmware scan
sudo ./emba -l ./logs -f /path/to/firmware.bin

# Run with AI-assisted analysis (requires OpenAI API key)
export OPENAI_API_KEY="your-api-key"
sudo ./emba -l ./logs -f /path/to/firmware.bin -p ./scan-profiles/default-scan-gpt.emba
```

### 7.5 Other Firmware Tools

```bash
# Firmware Mod Kit
git clone https://github.com/rampageX/firmware-mod-kit.git

# Jefferson (JFFS2 extraction)
pip3 install --user jefferson

# UBI Reader
pip3 install --user ubi_reader

# Sasquatch (SquashFS with vendor modifications)
sudo apt install -y sasquatch

# fmk (firmware mod kit)
sudo apt install -y firmware-mod-kit
```

---

## Part 8: AI-Powered Reverse Engineering Tools

### 8.1 GhidraMCP - AI-Assisted Ghidra

GhidraMCP allows LLMs like Claude to autonomously reverse engineer binaries through Ghidra.

**Installation:**
```bash
# Download latest release
# https://github.com/LaurieWired/GhidraMCP/releases

# Install the Ghidra plugin:
# 1. Open Ghidra
# 2. File → Install Extensions
# 3. Add the GhidraMCP zip file

# Install Python bridge
pip3 install --user mcp

# Clone for examples
git clone https://github.com/LaurieWired/GhidraMCP.git
cd GhidraMCP
pip3 install -r requirements.txt
```

**Configure Claude Desktop:**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "ghidra": {
      "command": "python",
      "args": [
        "/path/to/GhidraMCP/bridge_mcp_ghidra.py",
        "--ghidra-server", "http://127.0.0.1:8080/"
      ]
    }
  }
}
```

**Start Ghidra MCP server:**
```bash
# In Ghidra, start the HTTP server (check GhidraMCP docs)
# Then in terminal:
python bridge_mcp_ghidra.py --ghidra-server http://127.0.0.1:8080/
```

### 8.2 GhidrAssistMCP (Alternative - No Python Required)

```bash
# Download from: https://github.com/studio-b4/GhidrAssistMCP/releases

# Install in Ghidra:
# File → Install Extensions → Add zip file
# File → Configure → Developer → Enable GhidrAssistMCP

# MCP server starts automatically on port 8888
# Configure Claude Desktop with SSE transport
```

### 8.3 pyghidra-mcp (Headless Multi-Binary Analysis)

```bash
# Install pyghidra
pip3 install --user pyghidra

# Clone pyghidra-mcp
git clone https://github.com/clearbluejar/pyghidra-mcp.git
cd pyghidra-mcp
pip3 install -r requirements.txt

# This enables analyzing entire Ghidra projects (multiple binaries)
# Perfect for CI/CD and automated analysis
```

### 8.4 Radare2 MCP Server

```bash
# Install radare2-mcp
git clone https://github.com/radareorg/radare2-mcp.git
cd radare2-mcp
pip3 install -r requirements.txt

# Or install r2ai directly
pip3 install --user r2ai
```

**Configure Claude Desktop:**
```json
{
  "mcpServers": {
    "radare2": {
      "command": "python",
      "args": ["/path/to/radare2-mcp/server.py"]
    }
  }
}
```

### 8.5 IDA Pro MCP (If You Have IDA License)

```bash
# mrexodia's IDA Pro MCP
git clone https://github.com/mrexodia/ida-pro-mcp.git
cd ida-pro-mcp

# Install plugin
python install.py --install-plugin

# Configure Claude Desktop
```

---

## Part 9: IoT Security with AI (IoTHackBot)

IoTHackBot provides Claude Code skills for hybrid IoT pentesting.

### 9.1 Install IoTHackBot

```bash
git clone https://github.com/BrownFineSecurity/iothackbot.git
cd iothackbot

# Install as package
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
export PATH="$PATH:$(pwd)/bin"
```

### 9.2 Available Claude Skills

IoTHackBot includes these Claude Code skills:

| Skill | Purpose |
|-------|---------|
| **picocom** | UART console interaction for IoT devices |
| **wsdiscovery** | Discover ONVIF cameras and WS-Discovery devices |
| **IoTNet** | Network traffic analysis for IoT protocols |
| **telnetshell** | Telnet interaction for IoT pentesting |
| **mqttscan** | MQTT broker security testing |
| **onvifscan** | ONVIF camera security testing |

### 9.3 Using IoTHackBot Tools

```bash
# Discover ONVIF devices on network
wsdiscovery 239.255.255.250

# Test ONVIF camera authentication
onvifscan auth http://192.168.1.100 --all

# Scan MQTT broker
mqttscan 192.168.1.100

# Firmware analysis
sudo ffind firmware.bin -e

# Connect to UART (with Claude skill)
# Install picocom skill in Claude, then ask Claude to connect
```

---

## Part 10: ChipWhisperer Setup (Advanced Glitching/SCA)

### 10.1 Install ChipWhisperer

**Linux (Recommended):**
```bash
# Create virtual environment
python3 -m venv ~/chipwhisperer-venv
source ~/chipwhisperer-venv/bin/activate

# Install ChipWhisperer
pip install chipwhisperer

# Clone for tutorials
git clone https://github.com/newaetech/chipwhisperer.git
cd chipwhisperer
git submodule update --init jupyter

# Install udev rules
sudo cp 50-newae.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo groupadd -f chipwhisperer
sudo usermod -aG chipwhisperer $USER
```

**macOS:**
```bash
# ChipWhisperer works but some features limited
pip3 install --user chipwhisperer
```

### 10.2 Run ChipWhisperer Tutorials

```bash
source ~/chipwhisperer-venv/bin/activate
cd ~/chipwhisperer/jupyter
jupyter notebook

# Open "0 - Introduction to Jupyter Notebooks.ipynb"
```

---

## Part 11: Protocol Analysis Tools

### 11.1 Logic Analysis - sigrok/PulseView

```bash
# macOS:
brew install sigrok-cli
brew install --cask pulseview

# Linux:
sudo apt install -y sigrok sigrok-cli pulseview libsigrok-dev
```

**Supported analyzers:**
- Saleae Logic (via sigrok)
- DSLogic
- Curious Bolt LA
- Bus Pirate SUMP mode

### 11.2 Wireshark for USB Analysis

```bash
# macOS:
brew install --cask wireshark

# Linux:
sudo apt install -y wireshark tshark

# Enable USB capture (Linux)
sudo modprobe usbmon
sudo setfacl -m u:$USER:r /dev/usbmon*
```

### 11.3 Serial Terminal Tools

```bash
# tio (recommended - auto-reconnect)
# macOS:
brew install tio

# Linux:
sudo apt install -y tio

# Usage:
tio /dev/ttyACM0
# Exit with: Ctrl-T Q

# Alternative: picocom
sudo apt install -y picocom
picocom -b 115200 /dev/ttyACM0
```

---

## Part 12: Debug Interface Tools

### 12.1 OpenOCD (JTAG/SWD)

```bash
# macOS:
brew install openocd

# Linux:
sudo apt install -y openocd

# Or build from source for latest
git clone https://github.com/openocd-org/openocd.git
cd openocd
./bootstrap
./configure
make
sudo make install
```

### 12.2 OpenOCD with Your Hardware

**Bus Pirate as JTAG:**
```bash
openocd -f interface/buspirate.cfg -f target/stm32f1x.cfg
```

**GreatFET as debugger:**
```bash
# GreatFET can act as JTAG/SWD adapter
# Check GreatFET documentation for specifics
```

### 12.3 GDB for Debugging

```bash
# Install GDB with ARM support
# macOS:
brew install arm-none-eabi-gdb

# Linux:
sudo apt install -y gdb-multiarch arm-none-eabi-gdb

# Connect to OpenOCD
gdb-multiarch firmware.elf
(gdb) target remote localhost:3333
(gdb) monitor reset halt
(gdb) load
(gdb) continue
```

---

## Part 13: Workspace Organization

### 13.1 Directory Structure

```bash
mkdir -p ~/hardware_hacking/{projects,tools,firmware,scripts,docs,dumps}
mkdir -p ~/hardware_hacking/tools/{buspirate,greatfet,curious_bolt,faulty_cat,shikra}
mkdir -p ~/hardware_hacking/projects/{active,archive}
mkdir -p ~/hardware_hacking/firmware/{extracted,modified,backups}
mkdir -p ~/hardware_hacking/mcp_servers

# Clone tool repositories
cd ~/hardware_hacking/tools
git clone https://github.com/DangerousPrototypes/BusPirate5-firmware.git buspirate/firmware
git clone https://github.com/greatscottgadgets/greatfet.git
git clone https://github.com/ElectronicCats/faultycat.git faulty_cat/
git clone https://github.com/LaurieWired/GhidraMCP.git ../mcp_servers/ghidra_mcp
git clone https://github.com/BrownFineSecurity/iothackbot.git ../mcp_servers/iothackbot
```

### 13.2 Shell Configuration

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Hardware Hacking Environment
export HARDWARE_HOME="$HOME/hardware_hacking"
export PATH="$PATH:$HARDWARE_HOME/scripts"
export PYTHONPATH="$PYTHONPATH:$HARDWARE_HOME/tools"

# Tool paths
export GHIDRA_HOME="$HOME/ghidra"
export PATH="$PATH:$GHIDRA_HOME"

# GreatFET/FaceDancer backend
export BACKEND=greatfet

# ChipWhisperer virtual environment
alias cw='source ~/chipwhisperer-venv/bin/activate'

# Quick device aliases (adjust paths as needed)
alias bp='tio /dev/ttyACM0'
alias gf='greatfet info'
alias la='pulseview &'

# Firmware analysis
alias fw-extract='binwalk -Me'
alias fw-entropy='binwalk -E'
alias fw-strings='strings -n 8'

# Flash operations
alias flash-read='flashrom -p ft2232_spi:type=232H -r'
alias flash-write='flashrom -p ft2232_spi:type=232H -w'
```

---

## Part 14: Quick Reference

### Device Detection
```bash
# Find all connected hardware
# macOS:
system_profiler SPUSBDataType | grep -A5 -E "Bus Pirate|GreatFET|Electronic Cats|FTDI"

# Linux:
lsusb | grep -E "1209|1d50|0403|2e8a"
dmesg | tail -20  # After connecting device
```

### Common Serial Connections
```bash
# Bus Pirate
tio /dev/ttyACM0

# GreatFET shell
gf shell

# Generic serial
tio -b 115200 /dev/ttyUSB0
```

### Flash Operations Cheat Sheet
```bash
# With Shikra (fastest)
flashrom -p ft2232_spi:type=232H -r dump.bin

# With Bus Pirate
flashrom -p buspirate_spi:dev=/dev/ttyACM0,spispeed=1M -r dump.bin

# Identify chip only
flashrom -p ft2232_spi:type=232H -V
```

### Firmware Analysis Pipeline
```bash
# 1. Extract firmware
binwalk -Me firmware.bin
cd _firmware.bin.extracted

# 2. Check entropy (encryption?)
binwalk -E firmware.bin

# 3. Find interesting strings
strings -n 10 firmware.bin | grep -E "password|key|secret|admin"

# 4. Run EMBA (comprehensive)
sudo ./emba -l ./logs -f firmware.bin

# 5. Load in Ghidra for binary analysis
ghidraRun  # Then import binary
```

---

## Part 15: Troubleshooting

### Device Not Detected
```bash
# Linux - check dmesg
dmesg | tail -30

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Verify group membership
groups $USER  # Should show: dialout plugdev
```

### Permission Denied
```bash
# Linux
sudo usermod -a -G dialout,plugdev $USER
# Log out and back in!

# Temporary fix
sudo chmod 666 /dev/ttyACM0
```

### Python Package Issues
```bash
# Use virtual environment
python3 -m venv ~/hwhack-venv
source ~/hwhack-venv/bin/activate
pip install chipwhisperer greatfet facedancer binwalk
```

### Flashrom Chip Not Detected
```bash
# Force chip type if known
flashrom -p ft2232_spi:type=232H -c W25Q64.V -r dump.bin

# List all supported chips
flashrom -L | grep -i winbond
```

---

## Part 16: Learning Resources

### Books
1. **"The Hardware Hacking Handbook"** - Colin O'Flynn & Jasper van Woudenberg
2. **"Practical IoT Hacking"** - Fotios Chantzis et al.
3. **"The IoT Hacker's Handbook"** - Aditya Gupta

### Online Resources
- Bus Pirate Docs: https://docs.buspirate.com
- GreatFET Manual: https://greatfet.readthedocs.io
- ChipWhisperer Tutorials: https://chipwhisperer.readthedocs.io
- HardBreak Wiki: https://www.hardbreak.wiki
- VoidStar Security: https://voidstarsec.com

### Video Channels
- Joe Grand (hardware hacking)
- stacksmashing (hardware security)
- Colin O'Flynn (ChipWhisperer)
- LiveOverflow (security research)
- Matt Brown / Brown Fine Security (IoT pentesting)

### Practice
- ECSC23 challenges (included with Curious Bolt)
- IoTGoat - vulnerable firmware
- DVRF - Damn Vulnerable Router Firmware
- Rhme challenges

---

## Document Info
- **Version:** 3.0
- **Updated:** January 2026
- **Hardware Kit:** Bus Pirate + GreatFET One + Curious Bolt + Faulty Cat v2.1 + Shikra
- **Features:** Complete software setup, AI/MCP integrations, firmware analysis
