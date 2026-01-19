"""
Black Magic Probe backend using GDB Machine Interface.

The BMP is unique in that it has a built-in GDB server accessible via serial port.
No OpenOCD or other middleware needed - just connect GDB directly.

Reference: https://black-magic.org/
           https://github.com/blackmagic-debug/blackmagic

USB: Two CDC-ACM serial ports
  - Port 0 (/dev/ttyACM0 or ttyBmpGdb): GDB server
  - Port 1 (/dev/ttyACM1 or ttyBmpTarg): UART passthrough
"""

import subprocess
import re
from typing import Any, Optional

from .backends import (
    DebugBackend, register_backend
)
from .detect import DeviceInfo


class BlackMagicProbeBackend(DebugBackend):
    """
    Backend for Black Magic Probe using GDB Machine Interface.
    
    The BMP exposes a GDB server directly over USB serial, making it the 
    cleanest debug interface to work with. We communicate via GDB MI protocol
    or by spawning arm-none-eabi-gdb as a subprocess.
    
    Monitor commands available:
    - mon swdp_scan / mon jtag_scan  - Scan for targets
    - mon tpwr enable/disable        - Target power control
    - mon version                    - Firmware version
    - mon hard_srst                  - Hardware reset
    """
    
    # BMP USB VID/PID
    VID = 0x1D50
    PID = 0x6018  # Standard BMP
    
    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self._gdb_port = None    # GDB server serial port
        self._uart_port = None   # UART passthrough port
        self._gdb_proc = None    # GDB subprocess
        self._gdb_mi = None      # pygdbmi controller
        self._target_connected = False
        self._breakpoints = {}
        self._next_bp_id = 1
    
    def connect(self) -> bool:
        """Connect to Black Magic Probe."""
        # Find the GDB port (first of two serial ports)
        if not self._find_ports():
            return False
        
        # Try to use pygdbmi for clean GDB MI interface
        try:
            from pygdbmi.gdbcontroller import GdbController
            
            # Start GDB connected to BMP
            self._gdb_mi = GdbController(
                command=['arm-none-eabi-gdb', '--interpreter=mi3'],
                time_to_check_for_additional_output_sec=0.5
            )
            
            # Connect to BMP
            response = self._gdb_command(f'-target-select extended-remote {self._gdb_port}')
            
            if self._check_response(response, 'connected'):
                self._connected = True
                print(f"[BMP] Connected via pygdbmi on {self._gdb_port}")
                
                # Get firmware version
                version = self._monitor_command('version')
                if version:
                    print(f"[BMP] Firmware: {version}")
                
                return True
            
        except ImportError:
            print("[BMP] pygdbmi not installed, using subprocess fallback")
        except FileNotFoundError:
            print("[BMP] arm-none-eabi-gdb not found in PATH")
        except Exception as e:
            print(f"[BMP] pygdbmi connection failed: {e}")
        
        # Fallback: Direct serial communication for basic operations
        try:
            import serial
            
            self._serial = serial.Serial(
                self._gdb_port,
                baudrate=115200,
                timeout=1
            )
            self._connected = True
            self._using_serial_fallback = True
            print(f"[BMP] Connected via serial fallback on {self._gdb_port}")
            print("[BMP] Note: Limited functionality without GDB")
            return True
            
        except Exception as e:
            print(f"[BMP] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from BMP."""
        if self._gdb_mi:
            try:
                self._gdb_command('-gdb-exit')
                self._gdb_mi.exit()
            except Exception:
                pass
            self._gdb_mi = None
        
        if hasattr(self, '_serial') and self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        
        self._connected = False
        self._target_connected = False
        self._breakpoints.clear()
    
    def get_info(self) -> dict[str, Any]:
        """Get BMP information."""
        info = {
            "name": "Black Magic Probe",
            "gdb_port": self._gdb_port,
            "uart_port": self._uart_port,
            "target_connected": self._target_connected,
        }
        
        if self._connected and self._gdb_mi:
            version = self._monitor_command('version')
            if version:
                info["firmware"] = version
        
        return info
    
    # --------------------------------------------------------------------------
    # Port Discovery
    # --------------------------------------------------------------------------
    
    def _find_ports(self) -> bool:
        """Find BMP GDB and UART serial ports."""
        import serial.tools.list_ports
        
        bmp_ports = []
        
        for port in serial.tools.list_ports.comports():
            # Match by VID/PID
            if port.vid == self.VID and port.pid == self.PID:
                bmp_ports.append(port.device)
            # Match by description
            elif port.description and 'Black Magic' in port.description:
                bmp_ports.append(port.device)
            # Match by serial ID pattern on Linux
            elif 'ttyBmp' in port.device:
                bmp_ports.append(port.device)
        
        # Also check for symlinks on Linux
        import os
        from pathlib import Path
        
        for pattern in ['/dev/ttyBmpGdb', '/dev/ttyBmpGdb*']:
            from glob import glob
            for path in glob(pattern):
                if path not in bmp_ports:
                    bmp_ports.append(path)
        
        if not bmp_ports:
            # Use device port from detection if available
            if self.device.port:
                self._gdb_port = self.device.port
                print(f"[BMP] Using detected port: {self._gdb_port}")
                return True
            
            print("[BMP] No Black Magic Probe found")
            return False
        
        # Sort ports - GDB is typically first (lower number)
        bmp_ports.sort()
        
        self._gdb_port = bmp_ports[0]
        if len(bmp_ports) > 1:
            self._uart_port = bmp_ports[1]
        
        print(f"[BMP] Found GDB port: {self._gdb_port}")
        if self._uart_port:
            print(f"[BMP] Found UART port: {self._uart_port}")
        
        return True
    
    # --------------------------------------------------------------------------
    # GDB MI Communication
    # --------------------------------------------------------------------------
    
    def _gdb_command(self, command: str) -> list[dict]:
        """Send GDB MI command and return response."""
        if not self._gdb_mi:
            return []
        
        try:
            return self._gdb_mi.write(command, timeout_sec=5)
        except Exception as e:
            print(f"[BMP] GDB command failed: {e}")
            return []
    
    def _check_response(self, response: list[dict], success_indicator: str = 'done') -> bool:
        """Check if GDB response indicates success."""
        for msg in response:
            if msg.get('message') == success_indicator:
                return True
            if msg.get('type') == 'result' and msg.get('message') == 'done':
                return True
        return False
    
    def _monitor_command(self, cmd: str) -> Optional[str]:
        """Execute BMP monitor command and return output."""
        if not self._gdb_mi:
            return None
        
        response = self._gdb_command(f'-interpreter-exec console "monitor {cmd}"')
        
        # Extract console output
        output_lines = []
        for msg in response:
            if msg.get('type') == 'console':
                payload = msg.get('payload', '')
                output_lines.append(payload.strip())
        
        return '\n'.join(output_lines) if output_lines else None
    
    # --------------------------------------------------------------------------
    # Target Connection
    # --------------------------------------------------------------------------
    
    def connect_target(self, target: str = "auto") -> bool:
        """
        Connect to debug target via SWD or JTAG scan.
        
        Args:
            target: "swd", "jtag", or "auto" (tries SWD first)
        """
        if not self._connected:
            return False
        
        if not self._gdb_mi:
            print("[BMP] Target connection requires GDB MI interface")
            return False
        
        # Scan for targets
        if target == "auto" or target == "swd":
            scan_result = self._monitor_command('swdp_scan')
            if scan_result and 'Available Targets' in scan_result:
                print(f"[BMP] SWD scan:\n{scan_result}")
            elif target == "swd":
                print("[BMP] SWD scan found no targets")
                return False
        
        if target == "auto" or target == "jtag":
            if target == "auto" and self._target_connected:
                pass  # Already found via SWD
            else:
                scan_result = self._monitor_command('jtag_scan')
                if scan_result and 'Available Targets' in scan_result:
                    print(f"[BMP] JTAG scan:\n{scan_result}")
        
        # Attach to first target
        response = self._gdb_command('-target-attach 1')
        
        if self._check_response(response):
            self._target_connected = True
            print("[BMP] Attached to target 1")
            return True
        
        print("[BMP] Failed to attach to target")
        return False
    
    def set_target_power(self, enabled: bool) -> bool:
        """Enable/disable target power (tpwr)."""
        if not self._connected:
            return False
        
        cmd = 'tpwr enable' if enabled else 'tpwr disable'
        result = self._monitor_command(cmd)
        print(f"[BMP] Target power: {'enabled' if enabled else 'disabled'}")
        return True
    
    # --------------------------------------------------------------------------
    # Execution Control
    # --------------------------------------------------------------------------
    
    def halt(self) -> bool:
        """Halt the target CPU."""
        if not self._target_connected:
            return False
        
        response = self._gdb_command('-exec-interrupt')
        return self._check_response(response)
    
    def resume(self) -> bool:
        """Resume target execution."""
        if not self._target_connected:
            return False
        
        response = self._gdb_command('-exec-continue')
        return self._check_response(response, 'running')
    
    def reset(self, halt: bool = False) -> bool:
        """Reset target."""
        if not self._target_connected:
            return False
        
        # Use monitor command for reset
        if halt:
            self._monitor_command('hard_srst')
            # Re-attach and halt
            self._gdb_command('-target-attach 1')
            return self.halt()
        else:
            self._monitor_command('hard_srst')
            return True
    
    def step(self) -> bool:
        """Single-step the target."""
        if not self._target_connected:
            return False
        
        response = self._gdb_command('-exec-step')
        return self._check_response(response)
    
    # --------------------------------------------------------------------------
    # Memory Access
    # --------------------------------------------------------------------------
    
    def read_memory(self, address: int, size: int) -> bytes:
        """Read memory from target."""
        if not self._target_connected:
            return b''
        
        # GDB MI memory read
        response = self._gdb_command(f'-data-read-memory-bytes 0x{address:x} {size}')
        
        for msg in response:
            if msg.get('type') == 'result' and msg.get('payload'):
                payload = msg['payload']
                if 'memory' in payload:
                    # Parse memory contents
                    mem_data = payload['memory']
                    if isinstance(mem_data, list) and mem_data:
                        contents = mem_data[0].get('contents', '')
                        return bytes.fromhex(contents)
        
        return b''
    
    def write_memory(self, address: int, data: bytes) -> bool:
        """Write memory to target."""
        if not self._target_connected:
            return False
        
        hex_data = data.hex()
        response = self._gdb_command(f'-data-write-memory-bytes 0x{address:x} {hex_data}')
        return self._check_response(response)
    
    # --------------------------------------------------------------------------
    # Breakpoints
    # --------------------------------------------------------------------------
    
    def set_breakpoint(self, address: int) -> int:
        """Set hardware breakpoint."""
        if not self._target_connected:
            return 0
        
        response = self._gdb_command(f'-break-insert *0x{address:x}')
        
        for msg in response:
            if msg.get('type') == 'result' and msg.get('payload'):
                bkpt = msg['payload'].get('bkpt', {})
                gdb_num = int(bkpt.get('number', 0))
                
                if gdb_num:
                    bp_id = self._next_bp_id
                    self._next_bp_id += 1
                    self._breakpoints[bp_id] = {'gdb_num': gdb_num, 'address': address}
                    print(f"[BMP] Breakpoint {bp_id} set at 0x{address:08x}")
                    return bp_id
        
        return 0
    
    def remove_breakpoint(self, bp_id: int) -> bool:
        """Remove breakpoint by ID."""
        if bp_id not in self._breakpoints:
            return False
        
        gdb_num = self._breakpoints[bp_id]['gdb_num']
        response = self._gdb_command(f'-break-delete {gdb_num}')
        
        if self._check_response(response):
            del self._breakpoints[bp_id]
            return True
        
        return False
    
    # --------------------------------------------------------------------------
    # Registers
    # --------------------------------------------------------------------------
    
    def read_registers(self) -> dict[str, int]:
        """Read all CPU registers."""
        if not self._target_connected:
            return {}
        
        response = self._gdb_command('-data-list-register-values x')
        
        regs = {}
        for msg in response:
            if msg.get('type') == 'result' and msg.get('payload'):
                reg_values = msg['payload'].get('register-values', [])
                for reg in reg_values:
                    num = int(reg.get('number', -1))
                    value = reg.get('value', '0x0')
                    
                    # Map register numbers to names (ARM Cortex-M)
                    reg_names = {
                        0: 'r0', 1: 'r1', 2: 'r2', 3: 'r3',
                        4: 'r4', 5: 'r5', 6: 'r6', 7: 'r7',
                        8: 'r8', 9: 'r9', 10: 'r10', 11: 'r11',
                        12: 'r12', 13: 'sp', 14: 'lr', 15: 'pc',
                        16: 'xpsr'
                    }
                    
                    if num in reg_names:
                        try:
                            regs[reg_names[num]] = int(value, 16)
                        except ValueError:
                            pass
        
        return regs
    
    # --------------------------------------------------------------------------
    # Flash Operations
    # --------------------------------------------------------------------------
    
    def flash_program(self, address: int, data: bytes, verify: bool = True) -> bool:
        """Program flash memory."""
        if not self._target_connected:
            return False
        
        # Write data to a temp file and load via GDB
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            f.write(data)
            temp_path = f.name
        
        try:
            # Load binary to address
            response = self._gdb_command(
                f'-interpreter-exec console "restore {temp_path} binary 0x{address:x}"'
            )
            
            if verify:
                response = self._gdb_command(
                    f'-interpreter-exec console "compare-sections"'
                )
            
            return True
            
        finally:
            os.unlink(temp_path)
    
    def dump_firmware(self, start_address: int, size: int, chunk_size: int = 4096) -> bytes:
        """Dump firmware from target."""
        if not self._target_connected:
            return b''
        
        data = b''
        address = start_address
        remaining = size
        
        while remaining > 0:
            chunk = min(chunk_size, remaining)
            chunk_data = self.read_memory(address, chunk)
            
            if len(chunk_data) != chunk:
                print(f"\n[BMP] Read error at 0x{address:08x}")
                break
            
            data += chunk_data
            address += chunk
            remaining -= chunk
            
            progress = (size - remaining) * 100 // size
            print(f"\r[BMP] Dumping: {progress}% ({len(data)}/{size} bytes)", end='')
        
        print()
        return data
    
    # --------------------------------------------------------------------------
    # UART Passthrough
    # --------------------------------------------------------------------------
    
    def get_uart_port(self) -> Optional[str]:
        """Get the UART passthrough serial port path."""
        return self._uart_port
    
    def open_uart(self, baudrate: int = 115200):
        """
        Open UART passthrough port.
        
        Returns a pyserial Serial object for the UART port.
        """
        if not self._uart_port:
            return None
        
        import serial
        return serial.Serial(self._uart_port, baudrate=baudrate, timeout=1)


# Register backend
register_backend("blackmagic", BlackMagicProbeBackend)
