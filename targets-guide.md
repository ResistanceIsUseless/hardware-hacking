# Hardware Hacking Practice Targets Guide
## Finding and Exploiting IoT Devices for Security Research

---

## Your Current Targets

### 1. Amcrest Camera - Excellent Target!

Amcrest cameras have a history of security issues and are very hackable.

**Attack Surface:**
- UART debug port (usually on the PCB)
- SPI flash (firmware extraction)
- ONVIF protocol (network-based)
- RTSP stream (often weak auth)
- Web interface (classic web vulns)
- Telnet/SSH (often enabled with default creds)

**Network Reconnaissance:**
```bash
# Full port scan
nmap -sV -sC -p- 192.168.1.x

# Check for ONVIF
onvifscan http://192.168.1.x

# Try default credentials
# admin:admin
# admin:password
# admin:amcrest

# Check RTSP stream (often unauthenticated)
ffplay rtsp://192.168.1.x:554/cam/realmonitor?channel=1&subtype=0

# Check for Amcrest-specific port
nmap -p 37777 192.168.1.x
```

**Hardware Approach:**
1. Open the camera (usually 4 screws)
2. Look for 4-pin UART header (TX, RX, GND, VCC)
3. Use Bus Pirate to find baud rate (usually 115200)
4. You'll likely get a root shell or bootloader access

**Known Vulnerabilities to Research:**
- Search "Amcrest CVE" - there are many documented issues
- Default credential issues
- Command injection in web interface
- Unauthenticated RTSP access
- Hardcoded backdoor accounts in firmware

---

### 2. UniFi Camera - Harder but Rewarding

Ubiquiti devices are better secured but still interesting targets.

**Attack Surface:**
- Adopt process (how it joins the controller)
- Firmware update mechanism
- SSH access (if enabled)
- Local debug interfaces
- Inform protocol (controller communication)

**Getting Started:**
```bash
# UniFi cameras run Linux - try SSH if enabled
ssh ubnt@192.168.1.x
# Default credentials: ubnt/ubnt

# Firmware is usually signed, but worth extracting
# Download firmware from UI website, analyze with binwalk
wget https://dl.ui.com/firmwares/xxx/UVC-G3.bin
binwalk -Me UVC-G3.bin

# Check for inform protocol
nmap -p 8080,8443,8880,8843 192.168.1.x
```

**Why It's Harder:**
- Signed firmware updates
- More secure boot process
- Better credential management
- Active security team at Ubiquiti

**What You'll Learn:**
- How "proper" embedded security looks
- Secure boot concepts
- Signed firmware verification

---

### 3. ESP32 IoT Plugs - Perfect for Learning!

These are ideal practice targets because they're cheap, well-documented, and often have debug enabled.

**Attack Surface:**
- UART (almost always exposed)
- SPI flash (easy to dump)
- WiFi credentials stored in flash
- OTA update mechanism
- Cloud API endpoints
- BLE (on some models)

**Safety Warning:**
```
⚠️  DANGER: Smart plugs connect to mains voltage (120V/240V)
    ALWAYS unplug from wall before opening!
    Never work on a plugged-in device!
    Mains voltage can kill you!
```

**Hardware Hacking Approach:**
```bash
# 1. UNPLUG FROM MAINS FIRST!
# 2. Open the plug (usually clips or screws)
# 3. Identify ESP32/ESP8266 chip
# 4. Find UART pins (TX, RX, GND) - usually labeled or near ESP chip
# 5. Connect Bus Pirate at 115200 or 74880 baud

# Dump the flash with esptool (easier for ESP chips)
pip install esptool
esptool.py --port /dev/ttyUSB0 read_flash 0 0x400000 esp32_dump.bin

# Or use Shikra for direct SPI access
# ESP32 typically has 4MB SPI flash (W25Q32)
flashrom -p ft2232_spi:type=232H -c W25Q32.V -r esp32_dump.bin

# Extract secrets from dump
strings esp32_dump.bin | grep -iE "ssid|password|wifi|psk|key|token|api"

# Find hardcoded endpoints
strings esp32_dump.bin | grep -iE "http|mqtt|\.com|\.cn|api"
```

**Common ESP Baud Rates:**
- 74880 - Boot messages
- 115200 - Most common runtime
- 9600 - Some older devices
- 921600 - Fast debug mode

---

## Cheap Devices to Buy for Practice

### Tier 1: Super Cheap ($5-20) - Great for Destructive Testing

| Device | Price | Why It's Good | Notes |
|--------|-------|---------------|-------|
| **GL.iNet GL-MT300N-V2** | ~$20 | OpenWrt router, UART exposed | Tons of documentation |
| **TP-Link TL-WR841N** | ~$15 | Classic target, many writeups | Easy UART access |
| **Wyze Cam v2/v3** | ~$20 | UART root shell available | Active research community |
| **Sonoff Basic** | ~$5 | ESP8266-based, trivial to hack | Perfect first target |
| **Tuya smart plugs** | ~$8 | ESP-based, well documented | tuya-convert project |
| **NodeMCU/ESP32 dev board** | ~$5 | Practice without risk | No case to open |
| **Generic WiFi smart bulbs** | ~$8 | Usually ESP-based | Easy teardown |
| **Cheap IP cameras (no-name)** | ~$15 | Often terrible security | AliExpress specials |

### Tier 2: Medium Difficulty ($20-50)

| Device | Price | Why It's Good | Notes |
|--------|-------|---------------|-------|
| **Xiaomi Mi Router 4A** | ~$25 | UART + SPI, good challenge | Documented exploits exist |
| **Amazon Echo Dot (older gen)** | ~$20 used | ARM-based, interesting boot | MediaTek chip |
| **TP-Link Kasa smart plug** | ~$15 | WiFi + cloud reversing | Better security than Tuya |
| **Reolink cameras** | ~$30 | Similar to Amcrest | Good firmware RE target |
| **Old Android TV boxes** | ~$20 | ARM Linux, often insecure | Amlogic/Rockchip based |
| **Smart doorbells (generic)** | ~$25 | Camera + WiFi + sometimes BLE | Multiple attack surfaces |
| **Baby monitors** | ~$30 | Often hilariously insecure | Good RTSP targets |

### Tier 3: Interesting Challenges ($50+)

| Device | Price | Why It's Good | Notes |
|--------|-------|---------------|-------|
| **Flipper Zero targets** | varies | Buy broken/bricked ones | Learn by fixing |
| **MikroTik routers** | ~$30 used | RouterOS, good security | Winbox protocol |
| **Ubiquiti EdgeRouter X** | ~$50 used | Real enterprise gear | MIPS-based |
| **Smart locks (generic)** | ~$40 | BLE + physical security | Zigbee/Z-Wave models too |
| **Car OBD2 dongles** | ~$15 | CAN bus + BLE | ELM327 clones |
| **NAS devices (old)** | ~$40 used | ARM Linux, web interface | Synology/QNAP |
| **Old enterprise APs** | ~$20 used | Cisco, Aruba, Ruckus | Complex firmware |

---

## Where to Find Cheap Targets

| Source | What to Look For |
|--------|------------------|
| **Thrift stores** | Old routers, IP cameras, smart home devices |
| **eBay "for parts"** | Broken devices are fine - you just need the board |
| **Amazon Warehouse** | Returned IoT devices, heavy discount |
| **Facebook Marketplace** | "Smart home lot" sales |
| **Garage sales** | Old routers, baby monitors |
| **Ewaste recyclers** | Sometimes give away old equipment |
| **AliExpress** | Cheap clones, great for destructive testing |
| **Craigslist free section** | Old networking equipment |
| **r/homelabsales** | Used enterprise gear |
| **Goodwill/Salvation Army** | Surprisingly good finds |

**Pro Tips:**
- "For parts or not working" listings are often just fine
- Old firmware versions are often MORE vulnerable
- Generic Chinese brands often share firmware with name brands
- Buy multiples of cheap devices to have backups

---

## Suggested Learning Path

### Week 1-2: ESP32 Smart Plugs (Easiest)

**Goal:** Full firmware extraction and analysis

**Day 1: Physical Teardown**
```bash
# Safety first - UNPLUG FROM MAINS!
# Open plug carefully
# Identify ESP32/ESP8266 chip
# Find UART pins (TX, RX, GND)
# Photograph the PCB for reference
```

**Day 2: UART Access**
```bash
# Connect Bus Pirate to UART pins
# Try common baud rates
screen /dev/ttyACM0 115200
# If garbage, try 74880 (ESP boot messages)

# You should see boot messages or a shell
# Try pressing Enter to get a prompt
```

**Day 3: Flash Dump**
```bash
# Method 1: esptool via UART (easier)
esptool.py --port /dev/ttyUSB0 read_flash 0 0x400000 plug_firmware.bin

# Method 2: Shikra via SPI (if UART doesn't work)
# Connect to SPI flash chip directly
flashrom -p ft2232_spi:type=232H -c W25Q32.V -r plug_firmware.bin
```

**Day 4: Firmware Analysis**
```bash
# Extract filesystem
binwalk -Me plug_firmware.bin
cd _plug_firmware.bin.extracted

# Search for secrets
strings plug_firmware.bin | grep -iE "password|key|api|token|http|mqtt"
grep -r "password" .
grep -r "ssid" .

# Find interesting binaries
find . -name "*.so" -o -name "*.bin" | head -20
```

**Day 5: Document Findings**
- WiFi credentials storage location
- Cloud API endpoints
- Any hardcoded passwords
- OTA update mechanism

**What You'll Learn:** UART, SPI flash dumping, firmware extraction, basic RE

---

### Week 3-4: Amcrest Camera (Medium)

**Goal:** Get root shell, extract firmware, find vulnerabilities

**Day 1: Network Reconnaissance**
```bash
# Find the camera
nmap -sn 192.168.1.0/24 | grep -i amcrest

# Full port scan
nmap -sV -sC -p- <camera_ip>
# Look for: 80 (web), 554 (RTSP), 37777 (Amcrest), 23 (telnet)

# Try default credentials on web interface
# admin:admin, admin:password, admin:amcrest
```

**Day 2: Known Exploits**
```bash
# Search for CVEs
searchsploit amcrest

# Check for unauthenticated RTSP
ffplay rtsp://<ip>:554/cam/realmonitor?channel=1&subtype=0

# Try telnet (sometimes enabled)
telnet <ip> 23
```

**Day 3: Physical Teardown**
```bash
# Open camera (usually 4 screws)
# Find UART header (4 pins near main chip)
# Connect Bus Pirate at 115200 baud
screen /dev/ttyACM0 115200

# You'll likely get:
# - U-Boot bootloader prompt, OR
# - Linux root shell, OR
# - Login prompt (try root:root, admin:admin)
```

**Day 4: Dump SPI Flash**
```bash
# Use Shikra for speed
flashrom -p ft2232_spi:type=232H -r amcrest_firmware.bin

# Verify dump
binwalk amcrest_firmware.bin
# Should see: bootloader, kernel, squashfs/cramfs filesystem
```

**Day 5-7: Firmware Analysis**
```bash
# Extract everything
binwalk -Me amcrest_firmware.bin
cd _amcrest_firmware.bin.extracted

# Find credentials
find . -name "passwd" -o -name "shadow" 2>/dev/null
cat ./squashfs-root/etc/passwd
cat ./squashfs-root/etc/shadow  # Crack these hashes!

# Find hardcoded creds
grep -r "password" ./squashfs-root/
grep -r "admin" ./squashfs-root/etc/

# Look for backdoors
strings ./squashfs-root/usr/bin/* | grep -iE "backdoor|debug|test"

# Run EMBA for comprehensive analysis
sudo ./emba -l ./logs -f amcrest_firmware.bin
```

**What You'll Learn:** Network + hardware combo, firmware RE, credential extraction

---

### Week 5-6: UniFi Camera (Harder)

**Goal:** Understand secure boot, signed firmware, proper security

**Day 1: Firmware Analysis**
```bash
# Download official firmware from Ubiquiti
wget https://dl.ui.com/firmwares/.../UVC.bin

# Analyze structure
binwalk -e UVC.bin
file *

# Look for signatures, encryption
binwalk -E UVC.bin  # Entropy analysis - high entropy = encrypted
```

**Day 2: Research Phase**
- Read existing UniFi security research papers
- Understand the adopt process
- Research inform protocol

**Day 3: Physical Access**
```bash
# These are harder to open
# Look for hidden screws under rubber feet/labels
# Find debug headers (may be unpopulated)
# UART is likely present but may require soldering
```

**Day 4+: Compare Security Models**
Document the differences between Amcrest and UniFi:
- Firmware signing
- Boot verification
- Credential storage
- Update mechanism

**What You'll Learn:** How "proper" security looks, secure boot, why some devices are harder

---

## Project Ideas

### Project 1: WiFi Credential Harvester
Extract stored WiFi passwords from 5+ different IoT devices. Document:
- Where credentials are stored (NVS, plaintext file, encrypted?)
- How they're protected (or not)
- Create a tool to automate extraction

### Project 2: UART Shell Collection
Get root shells on 5 different devices via UART:
- Document pin locations
- Note baud rates
- Screenshot boot sequences
- Create a "UART cheat sheet" for each device

### Project 3: Firmware Diff Analysis
```bash
# Dump firmware version 1
flashrom -p ft2232_spi:type=232H -r firmware_v1.bin

# Update device to new version
# Dump firmware version 2
flashrom -p ft2232_spi:type=232H -r firmware_v2.bin

# Extract both
binwalk -Me firmware_v1.bin
binwalk -Me firmware_v2.bin

# Compare
diff -r _firmware_v1.bin.extracted _firmware_v2.bin.extracted > changes.txt

# Look for security patches
grep -E "password|auth|cve|fix|security" changes.txt
```

### Project 4: Cloud API Reversing
For any cloud-connected device:
1. Extract firmware
2. Find API endpoints
3. Capture traffic (mitmproxy)
4. Document the API
5. Look for auth bypasses

### Project 5: Glitching ESP32 Secure Boot (Advanced)
Use Curious Bolt to bypass ESP32 secure boot:
```python
# Target the signature verification during boot
# Glitch at the right moment to skip the check
# Requires precise timing and experimentation
```

### Project 6: Build a Vulnerable Device Lab
Create a documented collection of vulnerable devices:
- Each with known exploitation steps
- Photograph PCBs with UART/JTAG labeled
- Write tutorials for each
- Share with the community

---

## Quick Start: This Weekend

**Saturday Morning - ESP32 Plug (2-3 hours)**

1. **Unplug from mains** (seriously!)
2. Open the case
3. Find UART pins
4. Connect Bus Pirate
5. Get a shell or dump flash
6. Extract WiFi credentials
7. Document everything

**Saturday Afternoon - Amcrest Camera (2-3 hours)**

1. Network scan to find it
2. Try default creds on web interface
3. Check for open RTSP
4. Open the camera
5. Find UART
6. Get shell access

**Sunday - Firmware Analysis (4+ hours)**

1. Dump firmware from one device
2. Run binwalk extraction
3. Search for hardcoded secrets
4. Run EMBA scan
5. Write up findings

---

## Tools Quick Reference

| Task | Tool | Command |
|------|------|---------|
| Find device on network | nmap | `nmap -sn 192.168.1.0/24` |
| Port scan | nmap | `nmap -sV -sC -p- <ip>` |
| UART connection | tio | `tio /dev/ttyACM0` |
| SPI flash read | flashrom | `flashrom -p ft2232_spi:type=232H -r dump.bin` |
| ESP flash read | esptool | `esptool.py read_flash 0 0x400000 dump.bin` |
| Extract firmware | binwalk | `binwalk -Me firmware.bin` |
| Entropy analysis | binwalk | `binwalk -E firmware.bin` |
| String search | strings/grep | `strings dump.bin \| grep password` |
| Full analysis | EMBA | `sudo ./emba -l ./logs -f firmware.bin` |

---

## Safety Reminders

```
⚠️  ELECTRICAL SAFETY
    - ALWAYS unplug mains-powered devices before opening
    - Smart plugs, bulbs, and some cameras have mains voltage inside
    - 120V/240V can kill you
    - When in doubt, don't open it while plugged in

⚠️  LEGAL CONSIDERATIONS
    - Only test devices you own
    - Don't access others' networks or devices
    - Follow responsible disclosure if you find vulnerabilities
    - Document everything for your own protection

⚠️  ESD PROTECTION
    - Use ESD wrist strap when handling PCBs
    - Ground yourself before touching components
    - Store boards in anti-static bags
```

---

## Resources

**Firmware Analysis:**
- EMBA: https://github.com/e-m-b-a/emba
- Binwalk: https://github.com/ReFirmLabs/binwalk

**Device-Specific Research:**
- Wyze Cam hacking: https://github.com/HclX/WyzeHacks
- Tuya devices: https://github.com/ct-Open-Source/tuya-convert
- Amcrest research: Search "Amcrest CVE" and "Amcrest firmware analysis"

**Learning:**
- VoidStar Security: https://voidstarsec.com
- HardBreak Wiki: https://www.hardbreak.wiki
- /r/ReverseEngineering
- /r/netsec

---

*Document Version: 1.0 | January 2026*
