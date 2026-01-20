# Curious Bolt CTF Documentation

Documentation specific to using the Curious Bolt hardware for CTF challenges, particularly the ECSC23 target board that ships with the Bolt.

## Quick Links

| Document | Description |
|----------|-------------|
| [quickstart.md](quickstart.md) | Get started quickly with Bolt CTF challenges |
| [guide.md](guide.md) | Complete walkthrough of Bolt CTF challenges |
| [wiring.md](wiring.md) | Wiring diagrams for Bolt connections |
| [pinout.md](pinout.md) | Pin reference for Bolt and target boards |
| [quick-ref.md](quick-ref.md) | Quick reference card for commands and timing |
| [analysis.md](analysis.md) | Glitch-o-Bolt tool analysis and capabilities |
| [integration.md](integration.md) | Glitch-o-Bolt integration summary |

## About Curious Bolt

The Curious Bolt is an all-in-one hardware security tool featuring:

- **Crowbar voltage glitcher** - 8.3ns resolution for precise fault injection
- **Differential power scope** - 35MSPS for side-channel analysis
- **8-channel logic analyzer** - PulseView compatible
- **ECSC23 target board** - 4 hardware CTF challenges included

## Target Board Challenges

The ECSC23 target board (STM32F103) includes 4 progressive challenges:

1. **UART Password Bypass** - Glitch timing attacks on authentication
2. **RDP Bypass** - Defeat STM32 Read-out Protection via glitching
3. **Power Analysis** - Side-channel attack to extract secrets
4. **Advanced Glitching** - Multi-stage attacks combining techniques

## Getting Started

1. Read [quickstart.md](quickstart.md) for immediate hands-on
2. Follow [../setup.md](../../setup.md) for complete lab setup
3. Use [guide.md](guide.md) for detailed challenge walkthroughs
4. Reference [wiring.md](wiring.md) when connecting hardware

## Related Documentation

- [../../CBECSC23.md](../../CBECSC23.md) - Multi-tool approach to ECSC23 challenges
- [../../setup.md](../../setup.md) - Complete hardware lab setup including Bolt
- [../../hwh/tooling/glitch-o-bolt/](../../hwh/tooling/glitch-o-bolt/) - Glitch-o-Bolt Python tool

---

*Part of the [hardware-hacking](../../) repository*
