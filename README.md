# Hardware Hacking & Security Research

This repository combines **attack pattern education** with **practical hardware hacking** guides and tools. It teaches both the fundamental vulnerability patterns that recur across technologies AND hands-on hardware security techniques.

## Repository Structure

```
hardware-hacking/
├── attack-patterns/        # 11 vulnerability pattern guides
├── docs/                  # Additional documentation
│   ├── bolt-ctf/         # Curious Bolt CTF challenges
│   └── tools/            # Tool implementation docs
├── hwh/                   # Python CLI tool for hardware hacking
├── setup.md              # Hardware lab setup guide
├── targets-guide.md      # Target device selection
└── CBECSC23.md          # ECSC23 CTF walkthrough
```

## Quick Links

### Attack Patterns
**[📚 attack-patterns/](attack-patterns/)** - Vulnerability pattern guides

Understand the fundamental patterns behind common vulnerabilities. Each guide teaches a transferable concept that applies across technologies:

- [Memory Disclosure](attack-patterns/memory-disclosure.md) - Heartbleed, Wallbleed, length field attacks
- [Parser Differential](attack-patterns/parser-differential.md) - HTTP request smuggling, multi-parser bugs
- [Deserialization](attack-patterns/deserialization.md) - Object injection, RCE via untrusted data
- [Type Confusion](attack-patterns/type-confusion.md) - Memory corruption via incompatible types
- [TOCTOU](attack-patterns/toctou.md) - Race conditions, file system attacks
- [Canonicalization](attack-patterns/canonicalization.md) - Path traversal, encoding bypasses
- [Gadget Chains](attack-patterns/gadget-chains.md) - ROP, Java deserialization chains
- [State Confusion](attack-patterns/state-confusion.md) - Out-of-order operations
- [Truncation](attack-patterns/truncation.md) - Data length violations
- [Reference Confusion](attack-patterns/reference-confusion.md) - Identity/ownership bugs
- [Semantic Gap](attack-patterns/semantic-gap.md) - Layer interpretation differences

**[View all patterns →](attack-patterns/)**

### Hardware Security
**[🔧 setup.md](setup.md)** - Complete hardware lab setup (~$590 kit)

Set up a professional hardware hacking lab with:
- Bus Pirate v5/v6, GreatFET One, Curious Bolt, Faulty Cat, Tigard, ST-Link
- Firmware analysis tools (Ghidra, binwalk, OpenOCD)
- AI-assisted reverse engineering (GhidraMCP)
- Full setup for macOS (M-series) and ARM Linux

**[🎯 targets-guide.md](targets-guide.md)** - What to practice on

Safe, legal targets for learning:
- IoT devices to buy (~$30-100 each)
- Old hardware to practice on
- Legal considerations & responsible disclosure
- Day-by-day practice plans

**[🏆 CBECSC23.md](CBECSC23.md)** - Hardware CTF walkthrough

Multi-tool approach to the ECSC23 hardware challenges (STM32F103 target board):
- **Challenge 1**: UART bypass via voltage glitching
- **Challenge 2**: STM32 RDP (Read-out Protection) bypass
- **Challenge 3**: Power analysis / side-channel attacks
- **Challenge 4**: Advanced EMFI (electromagnetic fault injection)

Complete with wiring diagrams, Python scripts, and tool selection flowcharts.

### Tools & Software
**[⚙️ hwh/](hwh/)** - Python CLI tool for hardware hacking

Command-line tool with multi-backend support:
```bash
cd hwh && pip install -e .
hwh interactive        # TUI mode
hwh detect            # Find connected devices
hwh flash read 0x0 0x10000 dump.bin
hwh uart --baud 115200
```

Supports: Bus Pirate, Curious Bolt, ST-Link, Tigard, BlackMagic Probe

**[📖 docs/bolt-ctf/](docs/bolt-ctf/)** - Curious Bolt CTF guides

Specific documentation for the Curious Bolt hardware and ECSC23 target board.

**[🛠️ docs/tools/](docs/tools/)** - Tool implementation docs

Technical documentation for the hwh toolkit.

---

## Practice Platforms

### Reverse Engineering & Crackme Challenges

| Platform | Focus | Notes |
|----------|-------|-------|
| [crackmes.one](https://crackmes.one/) | RE challenges | Has an upcoming CTF competition starting February 2026 |
| [challenges.re](https://challenges.re/) | RE exercises | From the author of "Reverse Engineering for Beginners" - no solutions provided |
| [Nightmare](https://guyinatuxedo.github.io/index.html) | Binary exploitation/RE | 90+ challenges with detailed writeups, great linear progression |
| [exploit.education](https://exploit.education/) | Binary exploitation | VMs for learning various security issues |
| [ROP Emporium](https://ropemporium.com/) | Return-oriented programming | Focused specifically on ROP chains |
| [CryptoHack](https://cryptohack.org/) | Cryptography | Fun crypto-specific challenges |
| [CTFlearn](https://ctflearn.com/) | General CTF | Learn and compete |

### Hardware Hacking & IoT Focused

| Platform | Focus | Notes |
|----------|-------|-------|
| [Microcorruption](https://microcorruption.com/) | Embedded security | Browser-based debugger with MSP430 assembly - challenges you to bypass fictional embedded locks. Excellent intro without buying hardware. |
| [DVRF](https://github.com/praetorian-inc/DVRF) | Router firmware | Damn Vulnerable Router Firmware - learn MIPS exploitation. Can run in QEMU if you don't have the E1550 hardware. |
| [IoTGoat](https://github.com/OWASP/IoTGoat) | IoT firmware | Deliberately insecure firmware based on OpenWrt |
| [Rhme (Riscure Hack Me)](https://github.com/Riscure/Rhme-2016) | Hardware CTF | Hardware CTF challenges from 2015-2018 |
| [Hack The Box - Hardware](https://www.hackthebox.com/) | Hardware system hacking | Part of their broader CTF platform |
| [Ph0wn CTF](https://ph0wn.org/) | Smart devices/IoT | Jeopardy-style CTF dedicated to IoT, embedded systems, smartphones - local event in France but archives available |
| [IoT Village CTF (DEF CON)](https://www.iotvillage.org/) | Real IoT devices | DEF CON Black Badge awarded contest - exploits real-world vulnerabilities on actual devices (30+ devices) |

---

## Legal & Ethical Notice

All content in this repository is for **authorized security testing, defensive security, CTF challenges, and educational purposes only**.

- Only test devices you own or have explicit written authorization to test
- Follow responsible disclosure for any vulnerabilities found in real products
- Respect the Computer Fraud and Abuse Act (US), Computer Misuse Act (UK), and local laws
- No destructive techniques, DoS attacks, mass targeting, or supply chain compromise

---

*Last Updated: January 2026*
