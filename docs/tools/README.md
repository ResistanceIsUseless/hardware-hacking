# Tools Documentation

Implementation documentation for the hardware hacking toolkit and associated software.

## Documents

| Document | Description |
|----------|-------------|
| [tui-implementation.md](tui-implementation.md) | Terminal UI implementation details for hwh tool |
| [multi-device.md](multi-device.md) | Multi-device support summary and architecture |
| [quickstart-tui.md](quickstart-tui.md) | Quick start guide for the TUI interface |

## hwh Command-Line Tool

The main hardware hacking toolkit is located at [../../hwh/](../../hwh/).

**Key features:**
- Multi-backend support (Bus Pirate, Bolt, ST-Link, Tigard, BlackMagic)
- Interactive and scripted modes
- Device detection and pin mapping
- Protocol analysis (UART, SPI, I2C)
- Flash operations
- Terminal UI for easier interaction

**Installation:**
```bash
cd hwh/
pip install -e .
```

**Usage:**
```bash
# Interactive mode
hwh interactive

# Device detection
hwh detect

# Flash operations
hwh flash read 0x08000000 0x10000 output.bin

# Protocol sniffing
hwh uart --baud 115200 --port /dev/ttyUSB0
```

See [../../hwh/README.md](../../hwh/README.md) for complete documentation.

## Related Documentation

- [../../hwh/](../../hwh/) - Main hwh tool directory
- [../../setup.md](../../setup.md) - Hardware lab setup
- [../bolt-ctf/](../bolt-ctf/) - Bolt-specific CTF guides

---

*Part of the [hardware-hacking](../../) repository*
