"""
ST-Link backend using pyocd for SWD/JTAG debug operations.

Supports: SWD, JTAG, firmware extraction, breakpoints, memory access
"""

from typing import Any, Optional

from .base import (
    DebugBackend, register_backend
)
from ..detect import DeviceInfo


class STLinkBackend(DebugBackend):
    """
    Backend for ST-Link debuggers using pyocd.
    
    pyocd provides a Python API for debug probe access, supporting:
    - Target connection/detection
    - Memory read/write
    - Register access
    - Breakpoints
    - Flash programming
    """
    
    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self._session = None
        self._target = None
        self._breakpoints = {}
        self._next_bp_id = 1
    
    def connect(self) -> bool:
        """Connect to ST-Link probe."""
        try:
            from pyocd.core.helpers import ConnectHelper
            from pyocd.core.session import Session
        except ImportError:
            print("[STLink] pyocd not installed")
            print("  Install with: pip install pyocd")
            return False
        
        try:
            # Create session - pyocd auto-detects ST-Link probes
            self._session = ConnectHelper.session_with_chosen_probe(
                unique_id=self.device.serial,
                auto_open=False
            )
            
            if self._session is None:
                print("[STLink] No probe found")
                return False
            
            self._session.open()
            self._connected = True
            print(f"[STLink] Connected to {self._session.probe.description}")
            return True
            
        except Exception as e:
            print(f"[STLink] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from ST-Link."""
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
            self._target = None
        self._connected = False
        self._breakpoints.clear()
    
    def get_info(self) -> dict[str, Any]:
        """Get probe and target information."""
        if not self._connected or not self._session:
            return {"error": "Not connected"}
        
        info = {
            "probe": self._session.probe.description,
            "probe_id": self._session.probe.unique_id,
        }
        
        if self._target:
            info["target"] = self._target.part_number
            info["state"] = str(self._target.get_state())
        
        return info
    
    # --------------------------------------------------------------------------
    # Target Connection
    # --------------------------------------------------------------------------
    
    def connect_target(self, target: str = "auto") -> bool:
        """
        Connect to debug target.
        
        Args:
            target: Target name (e.g., "stm32f103c8") or "auto" for auto-detect
        """
        if not self._connected or not self._session:
            return False
        
        try:
            if target == "auto":
                # Let pyocd auto-detect
                self._session.options.set('auto_target', True)
            else:
                self._session.options.set('target_override', target)
            
            # Get the target from the session's board
            board = self._session.board
            self._target = board.target
            
            print(f"[STLink] Target connected: {self._target.part_number}")
            return True
            
        except Exception as e:
            print(f"[STLink] Target connection failed: {e}")
            return False
    
    # --------------------------------------------------------------------------
    # Execution Control
    # --------------------------------------------------------------------------
    
    def halt(self) -> bool:
        """Halt the target CPU."""
        if not self._target:
            return False
        
        try:
            self._target.halt()
            return True
        except Exception as e:
            print(f"[STLink] Halt failed: {e}")
            return False
    
    def resume(self) -> bool:
        """Resume target execution."""
        if not self._target:
            return False
        
        try:
            self._target.resume()
            return True
        except Exception as e:
            print(f"[STLink] Resume failed: {e}")
            return False
    
    def reset(self, halt: bool = False) -> bool:
        """Reset target. If halt=True, halt after reset."""
        if not self._target:
            return False
        
        try:
            if halt:
                self._target.reset_and_halt()
            else:
                self._target.reset()
            return True
        except Exception as e:
            print(f"[STLink] Reset failed: {e}")
            return False
    
    def step(self) -> bool:
        """Single-step the target."""
        if not self._target:
            return False
        
        try:
            self._target.step()
            return True
        except Exception as e:
            print(f"[STLink] Step failed: {e}")
            return False
    
    # --------------------------------------------------------------------------
    # Memory Access
    # --------------------------------------------------------------------------
    
    def read_memory(self, address: int, size: int) -> bytes:
        """Read memory from target."""
        if not self._target:
            return b''
        
        try:
            return bytes(self._target.read_memory_block8(address, size))
        except Exception as e:
            print(f"[STLink] Memory read failed: {e}")
            return b''
    
    def write_memory(self, address: int, data: bytes) -> bool:
        """Write memory to target."""
        if not self._target:
            return False
        
        try:
            self._target.write_memory_block8(address, list(data))
            return True
        except Exception as e:
            print(f"[STLink] Memory write failed: {e}")
            return False
    
    def read_memory_32(self, address: int) -> Optional[int]:
        """Read a 32-bit word from memory."""
        if not self._target:
            return None
        
        try:
            return self._target.read32(address)
        except Exception as e:
            print(f"[STLink] Read32 failed: {e}")
            return None
    
    def write_memory_32(self, address: int, value: int) -> bool:
        """Write a 32-bit word to memory."""
        if not self._target:
            return False
        
        try:
            self._target.write32(address, value)
            return True
        except Exception as e:
            print(f"[STLink] Write32 failed: {e}")
            return False
    
    # --------------------------------------------------------------------------
    # Breakpoints
    # --------------------------------------------------------------------------
    
    def set_breakpoint(self, address: int) -> int:
        """
        Set hardware breakpoint.
        
        Returns breakpoint ID (>0) or 0 on failure.
        """
        if not self._target:
            return 0
        
        try:
            self._target.set_breakpoint(address)
            bp_id = self._next_bp_id
            self._next_bp_id += 1
            self._breakpoints[bp_id] = address
            print(f"[STLink] Breakpoint {bp_id} set at 0x{address:08x}")
            return bp_id
        except Exception as e:
            print(f"[STLink] Set breakpoint failed: {e}")
            return 0
    
    def remove_breakpoint(self, bp_id: int) -> bool:
        """Remove breakpoint by ID."""
        if not self._target or bp_id not in self._breakpoints:
            return False
        
        try:
            address = self._breakpoints[bp_id]
            self._target.remove_breakpoint(address)
            del self._breakpoints[bp_id]
            print(f"[STLink] Breakpoint {bp_id} removed")
            return True
        except Exception as e:
            print(f"[STLink] Remove breakpoint failed: {e}")
            return False
    
    def list_breakpoints(self) -> dict[int, int]:
        """List active breakpoints. Returns {bp_id: address}."""
        return self._breakpoints.copy()
    
    # --------------------------------------------------------------------------
    # Registers
    # --------------------------------------------------------------------------
    
    def read_registers(self) -> dict[str, int]:
        """Read all CPU registers."""
        if not self._target:
            return {}
        
        try:
            regs = {}
            core = self._target.selected_core
            
            # Read general purpose registers
            for i in range(16):
                regs[f"r{i}"] = core.read_core_register(f"r{i}")
            
            # Special registers
            regs["sp"] = regs["r13"]
            regs["lr"] = regs["r14"]
            regs["pc"] = regs["r15"]
            regs["xpsr"] = core.read_core_register("xpsr")
            
            return regs
            
        except Exception as e:
            print(f"[STLink] Read registers failed: {e}")
            return {}
    
    def write_register(self, name: str, value: int) -> bool:
        """Write a CPU register."""
        if not self._target:
            return False
        
        try:
            core = self._target.selected_core
            core.write_core_register(name, value)
            return True
        except Exception as e:
            print(f"[STLink] Write register failed: {e}")
            return False
    
    # --------------------------------------------------------------------------
    # Flash Operations
    # --------------------------------------------------------------------------
    
    def flash_program(self, address: int, data: bytes, verify: bool = True) -> bool:
        """
        Program flash memory.
        
        Args:
            address: Start address in flash
            data: Data to program
            verify: Verify after programming
        """
        if not self._target:
            return False
        
        try:
            from pyocd.flash.file_programmer import FileProgrammer
            
            # Create programmer and write data
            programmer = FileProgrammer(self._session)
            programmer.program(data, base_address=address)
            
            if verify:
                read_back = self.read_memory(address, len(data))
                if read_back != data:
                    print("[STLink] Flash verify failed")
                    return False
            
            print(f"[STLink] Programmed {len(data)} bytes at 0x{address:08x}")
            return True
            
        except Exception as e:
            print(f"[STLink] Flash program failed: {e}")
            return False
    
    def flash_erase(self, address: int, size: int) -> bool:
        """Erase flash sectors covering the given range."""
        if not self._target:
            return False
        
        try:
            flash = self._target.memory_map.get_flash_region_for_address(address)
            if flash:
                flash.flash.erase_page(address)
                return True
            return False
        except Exception as e:
            print(f"[STLink] Flash erase failed: {e}")
            return False
    
    # --------------------------------------------------------------------------
    # Firmware Dump
    # --------------------------------------------------------------------------
    
    def dump_firmware(self, 
                      start_address: int, 
                      size: int, 
                      chunk_size: int = 4096) -> bytes:
        """
        Dump firmware from target.
        
        Args:
            start_address: Start address
            size: Number of bytes to read
            chunk_size: Bytes per read operation (for progress)
            
        Returns:
            Firmware bytes
        """
        if not self._target:
            return b''
        
        data = b''
        address = start_address
        remaining = size
        
        while remaining > 0:
            chunk = min(chunk_size, remaining)
            chunk_data = self.read_memory(address, chunk)
            
            if len(chunk_data) != chunk:
                print(f"[STLink] Read error at 0x{address:08x}")
                break
            
            data += chunk_data
            address += chunk
            remaining -= chunk
            
            # Progress indicator
            progress = (size - remaining) * 100 // size
            print(f"\r[STLink] Dumping: {progress}% ({len(data)}/{size} bytes)", end='')
        
        print()  # Newline after progress
        return data


# Register this backend
register_backend("stlink", STLinkBackend)
