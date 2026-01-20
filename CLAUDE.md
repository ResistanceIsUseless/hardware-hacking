# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is an **educational security research repository** focused on understanding fundamental vulnerability patterns in hardware and embedded systems. It contains:

1. **Attack Pattern Guides** - Educational documentation of common vulnerability classes (memory disclosure, parser differential, deserialization, etc.)
2. **Hardware Hacking Setup & Practice** - Comprehensive guides for setting up a hardware security lab and safely practicing on owned devices
3. **ECSC23 Challenge Walkthrough** - Detailed walkthrough of European Cyber Security Challenge 2023 hardware security challenges

## Important Context: Security Research Ethics

This repository is for **authorized security testing, defensive security, CTF challenges, and educational purposes only**. When working in this repo:

- All attack patterns and techniques are documented for educational understanding and defensive security
- Hardware hacking guides explicitly emphasize only testing devices you own
- The repository includes legal and ethical considerations sections
- Proof-of-concept code is for demonstration on controlled lab environments

## Repository Structure

### Core Attack Pattern Guides (`*.md` files)

Each guide follows a consistent structure teaching the **transferable pattern** behind vulnerability classes:

- [attack-patterns/memory-disclosure.md](attack-patterns/memory-disclosure.md) - Length field attacks, buffer overreads (Heartbleed, Wallbleed patterns)
- [attack-patterns/parser-differential.md](attack-patterns/parser-differential.md) - Two systems interpret input differently
- [attack-patterns/deserialization.md](attack-patterns/deserialization.md) - Untrusted data → live objects
- [attack-patterns/type-confusion.md](attack-patterns/type-confusion.md) - Incompatible type access
- [attack-patterns/toctou.md](attack-patterns/toctou.md) - Time-of-check to time-of-use races
- [attack-patterns/canonicalization.md](attack-patterns/canonicalization.md) - Data transforms after security checks
- [attack-patterns/gadget-chains.md](attack-patterns/gadget-chains.md) - Chaining existing code for execution
- [attack-patterns/state-confusion.md](attack-patterns/state-confusion.md) - Out-of-order state machine operations
- [attack-patterns/truncation.md](attack-patterns/truncation.md) - Data shortened, meaning changed
- [attack-patterns/reference-confusion.md](attack-patterns/reference-confusion.md) - Resource identity/ownership confusion
- [attack-patterns/semantic-gap.md](attack-patterns/semantic-gap.md) - Layer interpretation differences

### Hardware Hacking Resources

- [setup.md](setup.md) - Complete hardware lab setup for macOS/Linux (Bus Pirate, GreatFET, Curious Bolt, Faulty Cat, Shikra)
- [targets-guide.md](targets-guide.md) - Target selection, device recommendations, safe practice methodology
- [CBECSC23.md](CBECSC23.md) - Multi-tool walkthrough of STM32F103 hardware challenges

### Key Documentation Principles

1. **Pattern-focused teaching** - Guides distill core concepts that transfer across technologies
2. **Practical examples** - Real CVEs (Heartbleed, Wallbleed) with byte-level analysis
3. **Multi-tool coverage** - Hardware guides cover multiple tools for same objective
4. **Safety-first** - Electrical safety warnings, legal considerations, ethical guidelines

## Common Development Tasks

### Adding a New Attack Pattern Guide

When creating a new pattern guide, follow the established structure:

1. **Title and Overview** - Clear description of the fundamental pattern
2. **Foundational Examples** - Real-world CVEs demonstrating the pattern
3. **Deep Dive** - Byte-level analysis showing how the vulnerability works
4. **Pattern Recognition** - Where else this appears, common variants
5. **Attack Surfaces** - Categories of products/systems affected
6. **Lab Setup & Methodology** - How to research/test safely
7. **Tools Reference** - Static/dynamic analysis tools
8. **Legal & Ethical Considerations** - What's permitted, what's not

### Updating Hardware Setup Guides

Hardware guides should include:

- **macOS and ARM Linux** commands (both platforms supported)
- **Tool-specific wiring diagrams** in ASCII art format
- **Complete Python examples** with clear docstrings
- **Troubleshooting sections** for common issues
- **Safety warnings** prominently placed (especially for mains voltage)

### Code Style for Proof-of-Concepts

Python PoC scripts follow these conventions:

```python
#!/usr/bin/env python3
"""
Brief description of what this demonstrates
CVE reference if applicable
For educational purposes only - note on authorization
"""

# Clear imports
import socket
import struct

# Descriptive function names explaining the attack step
def build_malicious_request():
    """
    Detailed docstring explaining:
    - What vulnerability this exploits
    - How the malicious data is structured
    - What the expected behavior is
    """
    pass

# Main execution with clear output
if __name__ == '__main__':
    # Usage example and results
    pass
```

## Architecture and Patterns

### Documentation Structure

The guides are **interconnected by patterns**, not by product categories:

- **Cross-referencing**: Guides reference related patterns (e.g., memory-disclosure → canonicalization for path traversal context)
- **Layered depth**: Start with core concept, progress to real examples, end with recognition/research methodology
- **CVE genealogy**: Track how vulnerabilities recur across vendors/products due to shared SDKs, libraries, code patterns

### Hardware Tool Selection Philosophy

The hardware guides emphasize **tool selection based on attack requirements**:

```
Need to talk protocols? → Bus Pirate (versatile, easy)
Need fast SPI dumps? → Shikra or Tigard (10x faster than Bus Pirate)
Need SWD/JTAG debugging? → ST-Link (STM32) or Tigard (general purpose)
Need precision glitching? → Curious Bolt (8.3ns resolution)
Need non-invasive attack? → Faulty Cat EMFI
Need side-channel analysis? → Curious Bolt (35MSPS scope)
Need to find debug pins? → Faulty Cat (detection) or Bus Pirate (logic analyzer)
```

**Critical Distinction:** Pin detection vs. actual debugging
- **Faulty Cat**: Can DETECT SWD/JTAG pins (like JTAGulator)
- **Bus Pirate**: Can help IDENTIFY pins via logic analyzer
- **ST-Link/Tigard**: Can actually USE SWD/JTAG for debugging/firmware extraction

This multi-tool approach teaches **when** to use each tool, not just **how**.

## Working with This Repository

### When Adding Content

1. **Maintain ethical framing** - All techniques for authorized testing only
2. **Include safety warnings** - Especially electrical safety for hardware
3. **Provide context** - Why this pattern matters, what systems it affects
4. **Show transferability** - How the pattern appears in different contexts
5. **Link related guides** - Help readers understand connections

### When Reading/Understanding

1. **Look for patterns, not exploits** - The goal is understanding fundamentals
2. **Check cross-references** - Guides reference each other for related patterns
3. **Note safety sections** - Legal and electrical safety are not optional
4. **Understand tool selection** - Hardware guides explain *why* each tool is chosen

### Common File Patterns

- All markdown files use **consistent heading structure** for navigation
- Python scripts include **detailed docstrings** explaining the attack vector
- Hardware wiring uses **ASCII diagrams** for clarity
- Commands show **both macOS and Linux** variants where they differ

## Technical Notes

### Hardware Tools Covered

- **Bus Pirate v5/v6** - Multi-protocol interface (UART, SPI, I2C), pin detection via logic analyzer
- **GreatFET One** - USB security testing, FaceDancer for USB emulation
- **Curious Bolt** - Voltage glitching (8.3ns), power analysis (35MSPS), logic analyzer
- **Faulty Cat v2.1** - EMFI (electromagnetic fault injection), SWD/JTAG pin detection (detection only, not debugging)
- **Tigard** - Multi-protocol (UART, SPI, I2C, JTAG, SWD) with OpenOCD support
- **Shikra** - Fast SPI flash dumping (no JTAG/SWD)
- **ST-Link v2** - **Required for STM32 SWD/JTAG debugging and firmware extraction**

### Software/Firmware Analysis Tools

- **Ghidra** - NSA's reverse engineering platform
- **Radare2** - Open source RE framework
- **EMBA** - Firmware security analyzer with AI support
- **binwalk** - Firmware extraction and analysis
- **OpenOCD** - SWD/JTAG debugging
- **flashrom** - SPI flash programming

### AI/MCP Integrations

Several guides reference AI-assisted reverse engineering tools:

- **GhidraMCP** - Claude integration for autonomous binary analysis
- **pyghidra-mcp** - Headless multi-binary analysis
- **IoTHackBot** - Claude Code skills for IoT pentesting

## Legal Framework

All content in this repository operates under these constraints:

1. **Only authorized testing** - Own devices, pentesting engagements, CTF competitions
2. **No destructive techniques** - DoS attacks, mass targeting, supply chain compromise prohibited
3. **Responsible disclosure** - If vulnerabilities found in real products
4. **Educational context** - Security research, defensive use cases

US: Computer Fraud and Abuse Act (CFAA)
EU: Computer Misuse Directive
UK: Computer Misuse Act

## Quick Reference

### File Organization

```
hardware-hacking/
├── README.md              # Overview and guide index
├── CLAUDE.md              # This file
├── *-disclosure.md        # Attack pattern guides (11 files)
├── setup.md               # Hardware lab setup
├── targets-guide.md       # Device selection and practice
└── CBECSC23.md           # Challenge walkthrough
```

### Key Concepts

- **Length field attacks** - Attacker controls length, server trusts it → memory disclosure
- **Parser differential** - Two parsers interpret differently → security gap
- **Voltage glitching** - Precise power disruption to bypass security checks
- **EMFI** - Electromagnetic fault injection, non-invasive attack
- **Side-channel analysis** - Power/timing leaks reveal secret data

### Pattern Recognition

When analyzing vulnerabilities, look for:

1. **Attacker-controlled lengths** trusted without validation
2. **Data transforms** after security checks (canonicalization)
3. **State machines** with missing state transition validation
4. **Multiple parsers** handling same input (differential)
5. **Time gaps** between check and use (TOCTOU)

---

*This repository teaches patterns, not exploits. Understanding these patterns helps build more secure systems and conduct authorized security research.*
