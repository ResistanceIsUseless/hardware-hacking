# Comprehensive Hardware Hacking Setup Guide
## macOS (M-series) and ARM Linux Configuration

### Overview
This guide covers the installation and configuration of tools for hardware security testing. It includes setup for common hardware interfaces, protocol analysis, fault injection, firmware extraction, and reverse engineering.

**Primary Hardware Covered:**
- **Curious Supplies Bolt** - Fault injection, power analysis, and logic analyzer platform
- **Electronic Cats Glitcher** - Voltage and clock glitching tool
- **Bus Pirate v6** - Universal bus interface and protocol analyzer

**Additional Recommended Hardware:**
- **Flipper Zero** - Multi-tool for RFID, NFC, Sub-GHz, IR, and GPIO
- **JTAGulator** - On-chip debug interface discovery
- **Saleae Logic Analyzer** - Professional protocol analysis
- **Proxmark3** - RFID/NFC security research
- **HackRF One** - Software-defined radio platform
- **ChipWhisperer** - Side-channel analysis and glitching

---

## System Prerequisites

### macOS Requirements
- macOS 12.0 or later (tested on Apple Silicon)
- Homebrew package manager
- Xcode Command Line Tools

### ARM Linux Requirements
- Debian/Ubuntu-based distribution (or equivalent package manager)
- Python 3.8+
- USB device permissions configured

---

## Part 1: Common Tools Installation

### 1.1 Python Environment Setup

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3 and pip
brew install python@3.11
brew install pipx
pipx ensurepath
```

**ARM Linux:**
```bash
# Update package lists
sudo apt update

# Install Python and development tools
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y pipx
pipx ensurepath
```

### 1.2 Essential Development Tools

**macOS:**
```bash
# Install build essentials
xcode-select --install

# Install USB and serial tools
brew install libusb libftdi
brew install screen minicom
brew install git
```

**ARM Linux:**
```bash
# Install build essentials and USB tools
sudo apt install -y build-essential git
sudo apt install -y libusb-1.0-0-dev libftdi1-dev
sudo apt install -y screen minicom picocom
sudo apt install -y usbutils
```

### 1.3 USB Permissions (Linux Only)

Create udev rules for hardware access without sudo:

```bash
# Create udev rules file
sudo nano /etc/udev/rules.d/99-hardware-hacking.rules
```

Add the following content:
```
# Bus Pirate v6
SUBSYSTEM=="usb", ATTR{idVendor}=="1209", ATTR{idProduct}=="7331", MODE="0666", GROUP="plugdev"

# Electronic Cats devices
SUBSYSTEM=="usb", ATTR{idVendor}=="1209", ATTR{idProduct}=="50b0", MODE="0666", GROUP="plugdev"

# FTDI devices (common for hardware hackers)
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", MODE="0666", GROUP="plugdev"

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

# ChipWhisperer
SUBSYSTEM=="usb", ATTR{idVendor}=="2b3e", MODE="0666", GROUP="plugdev"

# JTAGulator
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", MODE="0666", GROUP="plugdev"

# Generic USB serial converters
SUBSYSTEM=="tty", ATTRS{idVendor}=="1209", MODE="0666", GROUP="plugdev"
```

Apply the rules:
```bash
# Add your user to the plugdev and dialout groups
sudo usermod -a -G plugdev,dialout $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Log out and back in for group changes to take effect
```

---

## Part 2: Bus Pirate v6 Setup

### 2.1 Install Bus Pirate Software

**Both macOS and Linux:**
```bash
# Install using pipx (recommended for isolated environment)
pipx install pyBusPirateLite

# Alternative: Install Bus Pirate CLI tools via pip
pip3 install --user pyBusPirate
```

### 2.2 Install Official Firmware Tools

```bash
# Clone the official Bus Pirate repository
git clone https://github.com/BusPirate/BusPirate5-firmware.git
cd BusPirate5-firmware
```

### 2.3 Test Bus Pirate Connection

**Find the device:**
```bash
# macOS
ls /dev/tty.usbmodem*

# Linux
ls /dev/ttyACM* /dev/ttyUSB*
```

**Connect via screen:**
```bash
# Replace with your actual device path
# macOS example:
screen /dev/tty.usbmodem14201 115200

# Linux example:
screen /dev/ttyACM0 115200

# Exit screen with: Ctrl-A then K, then Y
```

**Test commands in Bus Pirate console:**
```
i          # Display device information and version
m          # Select mode menu (should show available protocols)
~          # Bus Pirate self-test
```

**Supported Protocols:**
- UART/Serial
- SPI
- I2C
- 1-Wire
- JTAG
- HD44780 LCD

---

## Part 3: Electronic Cats Glitcher Setup

### 3.1 Install Arduino IDE and Tools

**macOS:**
```bash
# Install Arduino IDE
brew install --cask arduino

# Install Arduino CLI (alternative)
brew install arduino-cli
```

**ARM Linux:**
```bash
# Download and install Arduino IDE
wget https://downloads.arduino.cc/arduino-ide/arduino-ide_latest_Linux_ARM64.AppImage
chmod +x arduino-ide_latest_Linux_ARM64.AppImage

# Or use snap
sudo snap install arduino
```

### 3.2 Configure Arduino for Electronic Cats Boards

**Add board manager URL:**
1. Open Arduino IDE
2. Go to Preferences (Arduino → Preferences on macOS)
3. Add to "Additional Board Manager URLs":
   ```
   https://electroniccats.github.io/Arduino_Boards_Index/package_electroniccats_index.json
   ```

**Install board definitions:**
1. Tools → Board Manager
2. Search for "Electronic Cats"
3. Install "Electronic Cats SAMD Boards"

### 3.3 Install ChipWhisperer (for glitching work)

```bash
# Install ChipWhisperer and dependencies
pipx install chipwhisperer

# Alternative if pipx has issues:
pip3 install --user chipwhisperer

# Install Jupyter for interactive work
pipx install jupyter
```

### 3.4 Test Glitcher Connection

**Identify the device:**
```bash
# macOS
ls /dev/cu.usbmodem*

# Linux
ls /dev/ttyACM*

# Check device details
# macOS
system_profiler SPUSBDataType | grep -A 10 "Electronic Cats"

# Linux
lsusb | grep -i "electronic\|1209"
```

---

## Part 4: Curious Supplies Bolt Setup

The Curious Supplies Bolt is a hardware hacking multi-tool featuring:
- 8-channel logic analyzer (100k pts sample memory, works with PulseView)
- 35MSPS differential power oscilloscope for side-channel analysis
- Voltage glitching capabilities

### 4.1 Install Bolt Software and Dependencies

```bash
# Install SoapySDR (software-defined radio framework)
# macOS:
brew install soapysdr

# Linux:
sudo apt install -y soapysdr-tools python3-soapysdr

# Install additional tools for power analysis
pip3 install --user numpy scipy matplotlib jupyter
```

### 4.2 Install PulseView for Logic Analysis

```bash
# macOS:
brew install --cask pulseview

# Linux:
sudo apt install -y pulseview sigrok-cli
```

### 4.3 Install Bolt-Specific Tools

```bash
# Install dependencies (typical for fault injection platforms)
pip3 install --user pyserial numpy pandas matplotlib

# Clone or download Bolt software repository
# (Check official Curious Supplies documentation for latest software)
```

### 4.4 Test Bolt Connection

```bash
# List USB devices to find Bolt
# macOS:
system_profiler SPUSBDataType

# Linux:
lsusb -v
dmesg | tail -20

# Identify the serial port
# macOS:
ls /dev/cu.usbserial* /dev/cu.usbmodem*

# Linux:
ls /dev/ttyUSB* /dev/ttyACM*
```

---

## Part 5: Additional Hardware Tools

### 5.1 JTAGulator - Debug Interface Discovery

The JTAGulator assists in identifying on-chip debug (OCD) interfaces including JTAG, ARM SWD, and UART from unknown test points.

**Purchase:** ~$175 from Parallax or Grand Idea Studio

**Setup:**
```bash
# Clone firmware repository
git clone https://github.com/grandideastudio/jtagulator.git

# Connect via serial terminal
screen /dev/ttyUSB0 115200
```

**Key Commands:**
- `V` - Set target voltage
- `U` - UART discovery
- `I` - IDCODE scan (JTAG)
- `B` - BYPASS scan (JTAG)

### 5.2 Flipper Zero - Multi-Protocol Tool

Portable device supporting Sub-GHz, NFC, RFID, infrared, and GPIO.

**Firmware Options:**
- Official firmware
- Unleashed firmware (additional features)
- RogueMaster firmware

**Setup:**
```bash
# Install qFlipper for firmware updates
# macOS:
brew install --cask qflipper

# Linux:
# Download AppImage from flipperzero.one
```

### 5.3 Proxmark3 - RFID/NFC Research

Professional RFID tool for reading, writing, and emulating 125kHz and 13.56MHz cards.

**Setup:**
```bash
# Clone Proxmark3 client
git clone https://github.com/RfidResearchGroup/proxmark3.git
cd proxmark3

# Build client
make clean && make -j

# Run client
./pm3
```

**Key Commands:**
- `hw tune` - Antenna tuning
- `hf search` - Search for high-frequency tags
- `lf search` - Search for low-frequency tags

### 5.4 HackRF One - Software Defined Radio

Wide-band SDR platform (1 MHz to 6 GHz).

**Setup:**
```bash
# macOS:
brew install hackrf

# Linux:
sudo apt install -y hackrf

# Test connection
hackrf_info
```

**Companion Software:**
- GNU Radio
- SDR# (Windows)
- GQRX
- Universal Radio Hacker

### 5.5 Logic Analyzers

**Budget Options:**
- DSLogic Plus (~$150) - 16 channels, 400MHz
- Kingst LA series (~$30-100)
- Saleae clones (not recommended for professional use)

**Professional:**
- Saleae Logic Pro 8/16 (~$500-1000)
- Excellent software, reliable hardware
- Analog + digital capture

**Setup for Saleae:**
```bash
# Download Logic 2 software from saleae.com
# Linux: AppImage available
# macOS: DMG installer
```

### 5.6 Oscilloscopes

**Entry Level (Hardware Hacking):**
- Rigol DS1054Z (~$400) - 4 channel, 50MHz (hackable to 100MHz)
- Siglent SDS1104X-E (~$400) - 4 channel, 100MHz

**Mid-Range:**
- Rigol MSO5074 (~$1000) - Mixed signal, 70MHz
- Siglent SDS2000X+ series

**Features to Look For:**
- Protocol decoding (UART, SPI, I2C)
- Deep memory for long captures
- FFT analysis
- Bandwidth appropriate for target (5-10x signal frequency)

### 5.7 Flash Programmers

**TL866II Plus (~$50):**
```bash
# Supports EPROM, EEPROM, Flash, SPI, I2C, 93Cxx
# Windows software, works in VM
# Many adapters available
```

**Flashrom (Software):**
```bash
# Linux:
sudo apt install -y flashrom

# Read SPI flash
flashrom -p ch341a_spi -r backup.bin

# Write SPI flash
flashrom -p ch341a_spi -w modified.bin
```

**CH341A Programmer (~$5):**
- Cheap SPI/I2C programmer
- Caution: Some versions output 5V instead of 3.3V

---

## Part 6: Firmware Analysis Tools

### 6.1 Binwalk - Firmware Extraction

The essential tool for analyzing and extracting firmware images.

```bash
# Install via pip
pip3 install --user binwalk

# Or install from source (recommended)
git clone https://github.com/ReFirmLabs/binwalk.git
cd binwalk
pip3 install .

# Basic scan
binwalk firmware.bin

# Extract embedded files
binwalk -e firmware.bin

# Recursive extraction
binwalk -Me firmware.bin

# Entropy analysis (detect encryption/compression)
binwalk -E firmware.bin
```

### 6.2 Ghidra - Reverse Engineering

NSA's open-source reverse engineering framework.

```bash
# Download from ghidra-sre.org
# Requires Java JDK 17+

# macOS:
brew install --cask ghidra

# Linux:
# Download and extract, run ghidraRun
```

**Key Features:**
- Multi-architecture support (ARM, MIPS, x86, etc.)
- Decompiler
- Scripting support (Python, Java)
- Collaborative analysis

### 6.3 Additional Analysis Tools

**Radare2:**
```bash
# macOS:
brew install radare2

# Linux:
sudo apt install -y radare2
```

**Binary Ninja:**
- Commercial tool with excellent UI
- Personal license available

**IDA Pro:**
- Industry standard (expensive)
- Free version available for non-commercial use

### 6.4 EMBA - Automated Firmware Analysis

Comprehensive firmware security analyzer.

```bash
# Clone EMBA
git clone https://github.com/e-m-b-a/emba.git
cd emba

# Run with Docker (recommended)
./emba -f /path/to/firmware.bin -l ./logs
```

### 6.5 Firmadyne - Firmware Emulation

Emulate and analyze Linux-based firmware.

```bash
git clone --recursive https://github.com/firmadyne/firmadyne.git
cd firmadyne
./download.sh
```

---

## Part 7: Protocol Analysis Software

### 7.1 PulseView/sigrok

Open-source logic analyzer software.

```bash
# macOS:
brew install --cask pulseview

# Linux:
sudo apt install -y pulseview sigrok-cli

# Scan for devices
sigrok-cli --scan

# Supported decoders
sigrok-cli --list-supported
```

**Supported Protocols:**
UART, SPI, I2C, JTAG, SDIO, CAN, 1-Wire, and 80+ more

### 7.2 Wireshark

Network protocol analyzer, also useful for USB analysis.

```bash
# macOS:
brew install --cask wireshark

# Linux:
sudo apt install -y wireshark
```

### 7.3 Serial Terminal Options

**tio (Modern, recommended):**
```bash
# macOS:
brew install tio

# Linux:
sudo apt install -y tio

# Usage
tio /dev/ttyUSB0 -b 115200
```

**minicom:**
```bash
minicom -D /dev/ttyUSB0 -b 115200
```

**screen:**
```bash
screen /dev/ttyUSB0 115200
# Exit: Ctrl-A, K, Y
```

**picocom:**
```bash
picocom -b 115200 /dev/ttyUSB0
# Exit: Ctrl-A, Ctrl-X
```

---

## Part 8: JTAG/SWD Debugging

### 8.1 OpenOCD - Open On-Chip Debugger

```bash
# macOS:
brew install open-ocd

# Linux:
sudo apt install -y openocd

# Test
openocd --version

# Example: Connect to STM32 via ST-Link
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg
```

### 8.2 Common Debug Adapters

- **ST-Link V2** (~$10-25) - STM32 devices
- **J-Link** (~$75-500) - Multi-architecture, fast
- **Bus Pirate** - Slow but versatile
- **FTDI-based** - Various breakout boards
- **Raspberry Pi** - Can be used as JTAG/SWD adapter

### 8.3 GDB for ARM Debugging

```bash
# macOS:
brew install arm-none-eabi-gdb

# Linux:
sudo apt install -y gdb-multiarch

# Connect to OpenOCD
gdb-multiarch
target remote localhost:3333
```

---

## Part 9: Wireless Security Tools

### 9.1 Ubertooth One - Bluetooth Analysis

```bash
# Linux:
sudo apt install -y ubertooth

# Spectrum analysis
ubertooth-specan

# Bluetooth sniffing
ubertooth-btbb -f
```

### 9.2 RTL-SDR

Budget software-defined radio (~$25).

```bash
# macOS:
brew install rtl-sdr

# Linux:
sudo apt install -y rtl-sdr

# Test
rtl_test
```

### 9.3 YARD Stick One

Sub-GHz wireless attacks.

```bash
# Install RFcat
pip3 install rfcat

# Usage
rfcat -r
```

---

## Part 10: Physical Tools

### 10.1 Soldering Equipment

**Recommended Stations:**
- Hakko FX-888D (~$100) - Reliable entry-level
- KSGER T12 (~$50) - Budget option
- JBC stations ($300+) - Professional

**Essential Supplies:**
- Fine tip (conical and chisel)
- Flux (rosin-based, no-clean)
- Solder wick and solder sucker
- Quality solder (63/37 or lead-free)
- Hot air rework station for SMD

### 10.2 Magnification

- USB microscope (~$30-100)
- Stereo microscope for precision work
- Head-mounted magnifier

### 10.3 Probing Equipment

- Multimeter (Fluke 117 recommended)
- Oscilloscope probes (matched to your scope)
- Logic analyzer clips
- PCBite probing system
- Pogo pins and test clips
- Fine-tip probes

### 10.4 Connectors and Adapters

- SOIC8/SOP8 clips
- PLCC extractors
- Various USB adapters
- Dupont jumper wires
- Breadboards

---

## Part 11: Security and Safety

### 11.1 ESD Protection
- Use ESD wrist straps when handling sensitive components
- Work on ESD-safe mats
- Store devices in anti-static bags
- Ground yourself before handling boards

### 11.2 Power Safety
- Never exceed voltage ratings on target devices
- Use current-limited power supplies
- Verify polarity before connecting power
- Keep a lab notebook of all configurations
- Use fused power connections when possible

### 11.3 Legal and Ethical Considerations
- Only test devices you own or have explicit permission to test
- Hardware hacking for security research must follow responsible disclosure
- Document all testing procedures and findings
- Understand local laws regarding hardware modification and security testing
- Respect intellectual property and licensing

---

## Part 12: Workspace Organization

### 12.1 Create Project Structure

```bash
# Create organized directory structure
mkdir -p ~/hardware_hacking/{projects,tools,firmware,scripts,docs,dumps}
mkdir -p ~/hardware_hacking/tools/{bus_pirate,glitcher,bolt,jtagulator}
mkdir -p ~/hardware_hacking/projects/{active,archive}
mkdir -p ~/hardware_hacking/firmware/{extracted,modified,backups}

# Clone useful repositories
cd ~/hardware_hacking/tools
git clone https://github.com/BusPirate/BusPirate5-firmware.git bus_pirate/firmware
git clone https://github.com/grandideastudio/jtagulator.git
git clone https://github.com/ReFirmLabs/binwalk.git
```

### 12.2 Environment Variables

Add to your shell profile (`~/.zshrc` on macOS, `~/.bashrc` on Linux):

```bash
# Hardware hacking environment
export HARDWARE_HOME="$HOME/hardware_hacking"
export PATH="$PATH:$HARDWARE_HOME/scripts"

# Add aliases for quick access
alias bp='screen /dev/ttyACM0 115200'  # Adjust device path
alias glitch='screen /dev/ttyACM1 115200'  # Adjust device path
alias la='pulseview'

# Python path for custom scripts
export PYTHONPATH="$PYTHONPATH:$HARDWARE_HOME/tools"

# Ghidra
export GHIDRA_HOME="/path/to/ghidra"
```

---

## Part 13: Troubleshooting

### Issue: Device not appearing in /dev/

**Solution:**
```bash
# Check if device is detected by system
# macOS:
ioreg -p IOUSB -l -w 0

# Linux:
dmesg | grep -i usb | tail -20
sudo udevadm monitor --environment --udev
```

### Issue: Permission denied when accessing serial port

**Linux Solution:**
```bash
# Verify group membership
groups $USER

# Should show: dialout plugdev (among others)
# If not, add to groups and logout/login
sudo usermod -a -G dialout,plugdev $USER
```

**macOS Solution:**
```bash
# Usually not needed, but check permissions
ls -la /dev/cu.* /dev/tty.*

# Reset USB if needed
sudo killall -STOP -c usbd
sudo killall -CONT -c usbd
```

### Issue: Bus Pirate not responding

**Solution:**
```bash
# Try different baud rates
screen /dev/ttyACM0 115200
# If blank, try:
# Ctrl-A, K (kill), Y (yes)
screen /dev/ttyACM0 921600

# Reset Bus Pirate by unplugging and reconnecting
# Enter bootloader mode if firmware update needed (check manual)
```

### Issue: Python package conflicts

**Solution:**
```bash
# Use virtual environment for isolation
python3 -m venv ~/hardware_hacking/venv
source ~/hardware_hacking/venv/bin/activate
pip install chipwhisperer pyserial pyBusPirate binwalk
```

### Issue: Binwalk extraction failures

**Solution:**
```bash
# Install extraction dependencies
sudo apt install -y squashfs-tools cramfsswap sasquatch \
    jefferson ubi_reader yaffshiv p7zip-full

# Try manual extraction
binwalk -D '.*' firmware.bin
```

---

## Part 14: Learning Resources

### Books
1. **"The Hardware Hacking Handbook"** by Jasper van Woudenberg & Colin O'Flynn - Essential reading
2. **"Practical IoT Hacking"** by Fotios Chantzis et al.
3. **"The IoT Hacker's Handbook"** by Aditya Gupta
4. **"Hardware Security: A Hands-on Learning Approach"** by Mark Tehranipoor

### Online Resources
1. **Bus Pirate Documentation:** http://dangerousprototypes.com/docs/Bus_Pirate
2. **ChipWhisperer Tutorials:** https://github.com/newaetech/chipwhisperer-jupyter
3. **VoidStar Security Wiki:** https://voidstarsec.com/hw-hacking-lab/vss-lab-guide
4. **HackTricks Hardware:** https://book.hacktricks.xyz/hardware-physical-access
5. **HardBreak Wiki:** https://www.hardbreak.wiki/

### Video Resources
- Joe Grand's YouTube channel - Practical hardware hacking
- LiveOverflow - Security research and exploitation
- stacksmashing - Hardware security research
- Colin O'Flynn's channel - ChipWhisperer tutorials

### Conferences & Training
- **DEF CON Hardware Hacking Village** - Annual hands-on workshops
- **Hardwear.io** - Hardware security conference
- **REcon** - Reverse engineering conference
- **Black Hat** - Hardware track presentations

### Practice Platforms
- **Rhme (Riscure Hack Me)** - CTF-style hardware challenges
- **IoTGoat** - Deliberately vulnerable firmware
- **DVRF (Damn Vulnerable Router Firmware)** - Practice target

### Community
- Reddit: r/embedded, r/ReverseEngineering, r/netsec
- Discord: Hardware Hacking servers
- Twitter/X: Follow hardware security researchers

---

## Part 15: Recommended Practice Projects

### Beginner
1. **UART Analysis:** Identify and read serial debug ports on consumer routers
2. **SPI Flash Dumping:** Extract firmware from SPI flash chips on old routers
3. **I2C Bus Exploration:** Communicate with sensors and EEPROMs
4. **Logic Analysis:** Decode SPI/I2C traffic with PulseView

### Intermediate
5. **Firmware Extraction:** Full extraction and analysis workflow
6. **JTAG Debugging:** Connect to debug ports, dump memory
7. **Voltage Glitching:** Simple timing attacks on microcontrollers
8. **RFID Cloning:** Basic card cloning with Proxmark3

### Advanced
9. **Power Analysis:** DPA on cryptographic operations
10. **Fault Injection:** Bypass security checks via glitching
11. **Custom Firmware:** Modify and reflash device firmware
12. **Side-Channel Attacks:** Full key extraction via SCA

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────-─────────┐
│ Quick Command Reference                                      |
├───────────────────────────────────────────────────────-──────┤
│ List USB devices:                                            │
│   macOS:  system_profiler SPUSBDataType                      │
│   Linux:  lsusb -v                                           │
│                                                              │
│ Find serial ports:                                           │
│   macOS:  ls /dev/cu.* /dev/tty.*                            │
│   Linux:  ls /dev/ttyACM* /dev/ttyUSB*                       │
│                                                              │
│ Connect to serial:                                           │
│   screen /dev/ttyACM0 115200                                 │
│   tio /dev/ttyACM0                                           │
│                                                              │
│ Bus Pirate self-test:                                        │
│   Connect via screen, then type: ~                           │
│                                                              │
│ Exit screen:                                                 │
│   Ctrl-A, K, Y                                               │
│                                                              │
│ Exit tio:                                                    │
│   Ctrl-T, Q                                                  │
│                                                              │
│ Check permissions (Linux):                                   │
│   groups $USER  (should show dialout, plugdev)               │
│                                                              │
│ Firmware Analysis:                                           │
│   binwalk -Me firmware.bin   (extract recursively)           │
│   binwalk -E firmware.bin    (entropy analysis)              │
│                                                              │
│ Flash operations:                                            │
│   flashrom -p ch341a_spi -r backup.bin (read)                │
│   flashrom -p ch341a_spi -w new.bin    (write)               │
└────────────────────────────────────────────────────────-─────┘
```

---

## Maintenance and Updates

### Regular Maintenance Tasks

```bash
# Update firmware for Bus Pirate (check releases)
# Update ChipWhisperer
pipx upgrade chipwhisperer

# Update Binwalk
pip3 install --upgrade binwalk

# Update system packages
# macOS:
brew update && brew upgrade

# Linux:
sudo apt update && sudo apt upgrade

# Update Proxmark3 client
cd ~/hardware_hacking/tools/proxmark3
git pull
make clean && make -j
```

---

## Document Version
- **Version:** 2.0
- **Last Updated:** January 2026
- **Platform:** macOS (Apple Silicon) and ARM Linux
- **Primary Tools:** Bus Pirate v6, Electronic Cats Glitcher, Curious Supplies Bolt
- **Extended Coverage:** JTAGulator, Flipper Zero, Proxmark3, HackRF, Logic Analyzers, Firmware Analysis

---

*This guide is maintained as a living document. Update as you discover new tools, techniques, or encounter platform-specific issues.*
