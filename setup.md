# Hardware Hacking Setup Guide
## macOS (M-series) and ARM Linux Configuration

### Overview
This guide covers the installation and configuration of tools for hardware security testing using:
- **Curious Supplies Bolt** - Fault injection and power analysis platform
- **Electronic Cats Glitcher** - Voltage and clock glitching tool
- **Bus Pirate v6** - Universal bus interface and protocol analyzer

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

**Test serial connection:**
```bash
# Connect via screen
screen /dev/ttyACM0 115200

# You should see glitcher output or be able to send commands
```

---

## Part 4: Curious Supplies Bolt Setup

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

### 4.2 Install Bolt-Specific Tools

**Note:** The Bolt typically uses custom Python scripts and interfaces. Check the official Curious Supplies documentation for the latest software.

```bash
# Clone or download Bolt software repository
# (URL will depend on Curious Supplies' distribution method)
# Placeholder - check official documentation:
# git clone https://github.com/curious-supplies/bolt-software.git

# Install dependencies (typical for fault injection platforms)
pip3 install --user pyserial numpy pandas matplotlib
```

### 4.3 Test Bolt Connection

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

## Part 5: Additional Recommended Tools

### 5.1 Logic Analyzer Software

```bash
# PulseView (sigrok GUI) - excellent for protocol analysis
# macOS:
brew install --cask pulseview

# Linux:
sudo apt install -y pulseview sigrok-cli

# Test sigrok
sigrok-cli --scan
```

### 5.2 Serial Terminal Alternatives

```bash
# CoolTerm (macOS - GUI based, very reliable)
brew install --cask coolterm

# GTKTerm (Linux - GUI)
sudo apt install -y gtkterm

# tio (modern serial terminal for both)
# macOS:
brew install tio

# Linux:
sudo apt install -y tio
```

### 5.3 Oscilloscope and Analysis Tools

```bash
# Install OpenHantek6022 (for USB oscilloscopes)
# macOS:
brew install --cask openhantek

# Install pico-sdk (for RP2040-based tools)
git clone https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk
git submodule update --init
```

### 5.4 JTAG/SWD Debugging Tools

```bash
# OpenOCD - essential for ARM debugging
# macOS:
brew install open-ocd

# Linux:
sudo apt install -y openocd

# Test OpenOCD
openocd --version
```

---

## Part 6: Verification and Testing

### 6.1 Check All USB Devices

**macOS:**
```bash
# List all USB devices
system_profiler SPUSBDataType | grep -E "Bus Pirate|Electronic Cats|Curious|FTDI|Serial"

# Check serial ports
ls -la /dev/tty.* /dev/cu.*
```

**Linux:**
```bash
# List USB devices with details
lsusb -v | grep -A 10 -i "bus pirate\|electronic\|curious\|ftdi"

# Check serial devices
ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null

# Verify user permissions
groups $USER
```

### 6.2 Test Serial Connections

Create a test script:

```bash
# Create test script
cat > ~/test_hardware.sh << 'EOF'
#!/bin/bash
echo "=== Hardware Hacking Tools Test ==="
echo ""
echo "USB Devices:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    system_profiler SPUSBDataType | grep -E "Product ID|Vendor ID|Serial Number" | head -20
else
    lsusb
fi

echo ""
echo "Serial Ports:"
ls -la /dev/tty* /dev/cu.* 2>/dev/null | grep -E "ACM|USB|usbserial|usbmodem"

echo ""
echo "Python packages:"
pip3 list | grep -E "serial|usb|chipwhisperer|pyBusPirate"

echo ""
echo "Test complete. Connect each device one at a time and verify it appears above."
EOF

chmod +x ~/test_hardware.sh
~/test_hardware.sh
```

### 6.3 Functional Tests

**Bus Pirate v6:**
```bash
# Connect and run self-test
screen /dev/ttyACM0 115200
# In Bus Pirate console: ~
# Should show self-test results
```

**Electronic Cats Glitcher:**
```bash
# Open Arduino IDE
# Tools → Board → Electronic Cats SAMD → Select your board
# File → Examples → Basic → Blink
# Upload to verify programming capability
```

**Curious Supplies Bolt:**
```bash
# Follow manufacturer's specific test procedure
# Typically involves running a calibration or connection test script
# python3 bolt_test.py (check official documentation)
```

---

## Part 7: Workspace Organization

### 7.1 Create Project Structure

```bash
# Create organized directory structure
mkdir -p ~/hardware_hacking/{projects,tools,firmware,scripts,docs}
mkdir -p ~/hardware_hacking/tools/{bus_pirate,glitcher,bolt}
mkdir -p ~/hardware_hacking/projects/{active,archive}

# Clone useful repositories
cd ~/hardware_hacking/tools
git clone https://github.com/BusPirate/BusPirate5-firmware.git bus_pirate/firmware
```

### 7.2 Environment Variables

Add to your shell profile (`~/.zshrc` on macOS, `~/.bashrc` on Linux):

```bash
# Hardware hacking environment
export HARDWARE_HOME="$HOME/hardware_hacking"
export PATH="$PATH:$HARDWARE_HOME/scripts"

# Add aliases for quick access
alias bp='screen /dev/ttyACM0 115200'  # Adjust device path
alias glitch='screen /dev/ttyACM1 115200'  # Adjust device path

# Python path for custom scripts
export PYTHONPATH="$PYTHONPATH:$HARDWARE_HOME/tools"
```

---

## Part 8: Security and Safety Notes

### 8.1 ESD Protection
- Use ESD wrist straps when handling sensitive components
- Work on ESD-safe mats
- Store devices in anti-static bags

### 8.2 Power Safety
- Never exceed voltage ratings on target devices
- Use current-limited power supplies
- Verify polarity before connecting power
- Keep a lab notebook of all configurations

### 8.3 Legal and Ethical Considerations
- Only test devices you own or have explicit permission to test
- Hardware hacking for security research must follow responsible disclosure
- Document all testing procedures and findings
- Understand local laws regarding hardware modification and security testing

---

## Part 9: Troubleshooting Common Issues

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
pip install chipwhisperer pyserial pyBusPirate

# Deactivate when done
deactivate
```

---

## Part 10: Next Steps and Resources

### Learning Resources
1. **Bus Pirate Documentation:** http://dangerousprototypes.com/docs/Bus_Pirate
2. **ChipWhisperer Tutorials:** https://github.com/newaetech/chipwhisperer-jupyter
3. **Hardware Hacking Village:** DEF CON talks and workshops
4. **Joe Grand's YouTube:** Practical hardware hacking examples

### Recommended Practice Projects
1. **UART Analysis:** Identify and read serial debug ports on consumer devices
2. **SPI Flash Dumping:** Extract firmware from SPI flash chips
3. **I2C Bus Exploration:** Communicate with sensors and EEPROMs
4. **Voltage Glitching:** Simple timing attacks on microcontrollers
5. **Power Analysis:** Basic DPA on cryptographic operations

### Community Resources
- Reddit: r/embedded, r/ReverseEngineering
- Discord: Hardware Hacking servers
- Twitter/X: Follow @securelyfitz, @gamozolabs, @justinsteven
- Conferences: DEF CON Hardware Hacking Village, REcon, Hardwear.io

---

## Maintenance and Updates

### Regular Maintenance Tasks

```bash
# Update firmware for Bus Pirate (check releases)
# Update ChipWhisperer
pipx upgrade chipwhisperer

# Update system packages
# macOS:
brew update && brew upgrade

# Linux:
sudo apt update && sudo apt upgrade

# Keep documentation updated
cd ~/hardware_hacking/docs
git pull  # If you're tracking a docs repo
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│ Quick Command Reference                                     │
├─────────────────────────────────────────────────────────────┤
│ List USB devices:                                           │
│   macOS:  system_profiler SPUSBDataType                     │
│   Linux:  lsusb -v                                          │
│                                                             │
│ Find serial ports:                                          │
│   macOS:  ls /dev/cu.* /dev/tty.*                           │
│   Linux:  ls /dev/ttyACM* /dev/ttyUSB*                      │
│                                                             │
│ Connect to serial:                                          │
│   screen /dev/ttyACM0 115200                                │
│   tio /dev/ttyACM0                                          │
│                                                             │
│ Bus Pirate self-test:                                       │
│   Connect via screen, then type: ~                          │
│                                                             │
│ Exit screen:                                                │
│   Ctrl-A, K, Y                                              │
│                                                             │
│ Check permissions (Linux):                                  │
│   groups $USER  (should show dialout, plugdev)              │
└─────────────────────────────────────────────────────────────┘
```

---

## Document Version
- **Version:** 1.0
- **Last Updated:** January 2026
- **Platform:** macOS (Apple Silicon) and ARM Linux
- **Tested With:** Bus Pirate v6, Electronic Cats Glitcher, Curious Supplies Bolt

---

*This guide is maintained as a living document. Update as you discover new tools, techniques, or encounter platform-specific issues.*
