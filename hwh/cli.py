"""
hwh CLI - Unified Hardware Hacking Tool

Command-line interface using Click.
"""

import sys
import json
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .detect import detect, list_devices, print_detected_devices
from .backends import get_backend, SPIConfig, I2CConfig, GlitchConfig


# --------------------------------------------------------------------------
# CLI Group
# --------------------------------------------------------------------------

@click.group()
@click.version_option(version=__version__)
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, verbose):
    """hwh - Unified Hardware Hacking Tool
    
    A single interface for ST-Link, Bus Pirate, Tigard, Curious Bolt, and FaultyCat.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose


# --------------------------------------------------------------------------
# Device Detection
# --------------------------------------------------------------------------

@cli.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.option('--all', 'show_all', is_flag=True, help='Include unknown devices')
def detect_cmd(as_json, show_all):
    """Detect connected hardware hacking tools."""
    devices = list_devices(include_unknown=show_all)
    
    if as_json:
        output = [
            {
                "name": d.name,
                "type": d.device_type,
                "port": d.port,
                "vid": f"{d.vid:04x}" if d.vid else None,
                "pid": f"{d.pid:04x}" if d.pid else None,
                "serial": d.serial,
                "capabilities": d.capabilities,
            }
            for d in devices
        ]
        click.echo(json.dumps(output, indent=2))
    else:
        print_detected_devices()


# Alias for convenience
cli.add_command(detect_cmd, name='detect')


# --------------------------------------------------------------------------
# SPI Commands
# --------------------------------------------------------------------------

@cli.group()
def spi():
    """SPI flash operations."""
    pass


@spi.command('dump')
@click.option('-d', '--device', help='Device type (buspirate, tigard)')
@click.option('-o', '--output', type=click.Path(), required=True, help='Output file')
@click.option('-a', '--address', default='0x0', help='Start address (hex)')
@click.option('-s', '--size', default='0x100000', help='Size in bytes (hex)')
@click.option('--speed', default=1000000, help='SPI speed in Hz')
def spi_dump(device, output, address, size, speed):
    """Dump SPI flash to file."""
    # Parse hex values
    start_addr = int(address, 16) if address.startswith('0x') else int(address)
    dump_size = int(size, 16) if size.startswith('0x') else int(size)
    
    # Find suitable device
    devices = detect()
    
    if device:
        dev_info = devices.get(device)
    else:
        # Auto-select first SPI-capable device
        for key, dev in devices.items():
            if 'spi' in dev.capabilities:
                dev_info = dev
                click.echo(f"Auto-selected: {dev.name}")
                break
        else:
            click.echo("No SPI-capable device found", err=True)
            sys.exit(1)
    
    if not dev_info:
        click.echo(f"Device '{device}' not found", err=True)
        sys.exit(1)
    
    backend = get_backend(dev_info)
    if not backend:
        click.echo(f"No backend for {dev_info.device_type}", err=True)
        sys.exit(1)
    
    with backend:
        # Configure SPI
        config = SPIConfig(speed_hz=speed)
        if not backend.configure_spi(config):
            click.echo("SPI configuration failed", err=True)
            sys.exit(1)
        
        # Read flash ID first
        flash_id = backend.spi_flash_read_id()
        click.echo(f"Flash ID: {flash_id.hex()}")
        
        # Dump flash
        click.echo(f"Reading {dump_size} bytes from 0x{start_addr:06x}...")
        
        data = b''
        chunk_size = 4096
        
        with click.progressbar(length=dump_size, label='Dumping') as bar:
            while len(data) < dump_size:
                remaining = dump_size - len(data)
                chunk = min(chunk_size, remaining)
                
                chunk_data = backend.spi_flash_read(start_addr + len(data), chunk)
                if not chunk_data:
                    click.echo("\nRead error", err=True)
                    break
                
                data += chunk_data
                bar.update(len(chunk_data))
        
        # Write to file
        Path(output).write_bytes(data)
        click.echo(f"Written {len(data)} bytes to {output}")


@spi.command('id')
@click.option('-d', '--device', help='Device type')
def spi_id(device):
    """Read SPI flash JEDEC ID."""
    devices = detect()
    
    # Find device
    dev_info = None
    if device:
        dev_info = devices.get(device)
    else:
        for key, dev in devices.items():
            if 'spi' in dev.capabilities:
                dev_info = dev
                break
    
    if not dev_info:
        click.echo("No SPI device found", err=True)
        sys.exit(1)
    
    backend = get_backend(dev_info)
    with backend:
        backend.configure_spi(SPIConfig())
        flash_id = backend.spi_flash_read_id()
        
        if flash_id:
            click.echo(f"JEDEC ID: {flash_id.hex()}")
            # Decode common IDs
            if flash_id[0] == 0xEF:
                click.echo("  Manufacturer: Winbond")
            elif flash_id[0] == 0xC2:
                click.echo("  Manufacturer: Macronix")
            elif flash_id[0] == 0x20:
                click.echo("  Manufacturer: Micron")


# --------------------------------------------------------------------------
# I2C Commands
# --------------------------------------------------------------------------

@cli.group()
def i2c():
    """I2C operations."""
    pass


@i2c.command('scan')
@click.option('-d', '--device', help='Device type')
def i2c_scan(device):
    """Scan I2C bus for devices."""
    devices = detect()
    
    dev_info = None
    if device:
        dev_info = devices.get(device)
    else:
        for key, dev in devices.items():
            if 'i2c' in dev.capabilities:
                dev_info = dev
                break
    
    if not dev_info:
        click.echo("No I2C device found", err=True)
        sys.exit(1)
    
    backend = get_backend(dev_info)
    with backend:
        backend.configure_i2c(I2CConfig())
        
        found = backend.i2c_scan()
        
        if found:
            click.echo(f"Found {len(found)} device(s):")
            for addr in found:
                click.echo(f"  0x{addr:02x}")
        else:
            click.echo("No devices found")


# --------------------------------------------------------------------------
# Debug Commands
# --------------------------------------------------------------------------

@cli.group()
def debug():
    """Debug/SWD operations."""
    pass


@debug.command('dump')
@click.option('-d', '--device', help='Device type (stlink)')
@click.option('-o', '--output', type=click.Path(), required=True, help='Output file')
@click.option('-a', '--address', required=True, help='Start address (hex)')
@click.option('-s', '--size', required=True, help='Size in bytes (hex)')
@click.option('-t', '--target', default='auto', help='Target chip name')
def debug_dump(device, output, address, size, target):
    """Dump firmware via SWD/JTAG."""
    start_addr = int(address, 16) if address.startswith('0x') else int(address)
    dump_size = int(size, 16) if size.startswith('0x') else int(size)
    
    devices = detect()
    
    dev_info = None
    if device:
        dev_info = devices.get(device)
    else:
        for key, dev in devices.items():
            if 'swd' in dev.capabilities or 'debug' in dev.capabilities:
                dev_info = dev
                break
    
    if not dev_info:
        click.echo("No debug probe found", err=True)
        sys.exit(1)
    
    backend = get_backend(dev_info)
    with backend:
        if not backend.connect_target(target):
            click.echo("Target connection failed", err=True)
            sys.exit(1)
        
        backend.halt()
        
        click.echo(f"Dumping {dump_size} bytes from 0x{start_addr:08x}...")
        data = backend.dump_firmware(start_addr, dump_size)
        
        Path(output).write_bytes(data)
        click.echo(f"Written {len(data)} bytes to {output}")


@debug.command('regs')
@click.option('-d', '--device', help='Device type')
@click.option('-t', '--target', default='auto', help='Target chip')
def debug_regs(device, target):
    """Read CPU registers."""
    devices = detect()
    
    dev_info = None
    if device:
        dev_info = devices.get(device)
    else:
        for key, dev in devices.items():
            if 'debug' in dev.capabilities:
                dev_info = dev
                break
    
    if not dev_info:
        click.echo("No debug probe found", err=True)
        sys.exit(1)
    
    backend = get_backend(dev_info)
    with backend:
        backend.connect_target(target)
        backend.halt()
        
        regs = backend.read_registers()
        for name, value in regs.items():
            click.echo(f"  {name:6s}: 0x{value:08x}")


# --------------------------------------------------------------------------
# Glitch Commands
# --------------------------------------------------------------------------

@cli.group()
def glitch():
    """Fault injection operations."""
    pass


@glitch.command('single')
@click.option('-d', '--device', help='Device type (bolt, faultycat)')
@click.option('-w', '--width', default=100, help='Glitch width in ns')
@click.option('-o', '--offset', default=0, help='Offset after trigger in ns')
def glitch_single(device, width, offset):
    """Trigger a single glitch."""
    devices = detect()
    
    dev_info = None
    if device:
        dev_info = devices.get(device)
    else:
        for key, dev in devices.items():
            if 'glitch' in dev.capabilities:
                dev_info = dev
                break
    
    if not dev_info:
        click.echo("No glitcher found", err=True)
        sys.exit(1)
    
    backend = get_backend(dev_info)
    with backend:
        config = GlitchConfig(width_ns=width, offset_ns=offset)
        backend.configure_glitch(config)
        backend.trigger()
        click.echo(f"Glitch triggered: {width}ns width, {offset}ns offset")


@glitch.command('sweep')
@click.option('-d', '--device', help='Device type')
@click.option('--width-min', default=50, help='Min width (ns)')
@click.option('--width-max', default=500, help='Max width (ns)')
@click.option('--width-step', default=10, help='Width step (ns)')
@click.option('--offset-min', default=0, help='Min offset (ns)')
@click.option('--offset-max', default=1000, help='Max offset (ns)')
@click.option('--offset-step', default=50, help='Offset step (ns)')
@click.option('--attempts', default=5, help='Attempts per setting')
@click.option('-o', '--output', type=click.Path(), help='Save results to JSON')
def glitch_sweep(device, width_min, width_max, width_step, 
                 offset_min, offset_max, offset_step, attempts, output):
    """Run glitch parameter sweep."""
    devices = detect()
    
    dev_info = None
    if device:
        dev_info = devices.get(device)
    else:
        for key, dev in devices.items():
            if 'glitch' in dev.capabilities:
                dev_info = dev
                break
    
    if not dev_info:
        click.echo("No glitcher found", err=True)
        sys.exit(1)
    
    backend = get_backend(dev_info)
    with backend:
        # Calculate total iterations
        width_steps = (width_max - width_min) // width_step + 1
        offset_steps = (offset_max - offset_min) // offset_step + 1
        total = width_steps * offset_steps * attempts
        
        click.echo(f"Running {total} glitch attempts...")
        
        results = backend.run_glitch_sweep(
            width_range=(width_min, width_max),
            width_step=width_step,
            offset_range=(offset_min, offset_max),
            offset_step=offset_step,
            attempts_per_setting=attempts
        )
        
        click.echo(f"Completed {len(results)} glitches")
        
        if output:
            Path(output).write_text(json.dumps(results, indent=2))
            click.echo(f"Results saved to {output}")


# --------------------------------------------------------------------------
# Interactive Shell
# --------------------------------------------------------------------------

@cli.command()
def shell():
    """Start interactive Python shell with hwh loaded."""
    try:
        from IPython import embed
        
        # Import useful things into namespace
        from hwh import detect, list_devices, get_backend
        from hwh.backends import SPIConfig, I2CConfig, UARTConfig, GlitchConfig
        
        devices = detect()
        
        click.echo("hwh Interactive Shell")
        click.echo("=" * 40)
        click.echo("Available:")
        click.echo("  devices     - Dict of detected devices")
        click.echo("  detect()    - Refresh device list")
        click.echo("  get_backend(device) - Get backend for device")
        click.echo("")
        
        embed(colors='neutral')
        
    except ImportError:
        click.echo("IPython not installed. Install with: pip install ipython")
        click.echo("Falling back to basic Python shell...")
        
        import code
        code.interact(local=locals())


# --------------------------------------------------------------------------
# Entry Point
# --------------------------------------------------------------------------

def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
