"""
Curious Bolt backend for voltage glitching, logic analysis, and DPA.

Reference: https://github.com/tjclement/bolt
           https://bolt.curious.supplies/docs/

The Bolt uses a custom Python library ('scope') that ships with the device.
This backend wraps that library or provides a compatible implementation.
"""

from typing import Any, Optional
import time

from .base import (
    GlitchBackend, register_backend,
    GlitchConfig, TriggerEdge
)
from ..detect import DeviceInfo


class BoltBackend(GlitchBackend):
    """
    Backend for Curious Bolt hardware hacking multi-tool.
    
    Capabilities:
    - Crowbar voltage glitcher (8.3ns resolution)
    - 8-channel logic analyzer (PulseView compatible)
    - Differential power analysis oscilloscope
    
    The Bolt's native library uses:
        from scope import Scope
        s = Scope()
        s.glitch.repeat = 60  # Duration in 8.3ns cycles
        s.trigger()
    """
    
    # Bolt timing constants
    CLOCK_PERIOD_NS = 8.3  # Single clock cycle duration
    
    def __init__(self, device: DeviceInfo):
        super().__init__(device)
        self._scope = None
        self._glitch_config = GlitchConfig()
        self._armed = False
    
    def connect(self) -> bool:
        """Connect to Curious Bolt."""
        # First, try to import the native Bolt library
        try:
            from scope import Scope
            self._scope = Scope()
            self._connected = True
            print(f"[Bolt] Connected via native 'scope' library")
            return True
        except ImportError:
            pass
        
        # Fallback: Direct serial implementation
        if not self.device.port:
            print(f"[Bolt] No port found and 'scope' library not available")
            print("  Install Bolt library from: https://github.com/tjclement/bolt/tree/main/lib")
            return False
        
        try:
            import serial
            self._serial = serial.Serial(
                self.device.port,
                baudrate=115200,
                timeout=1
            )
            self._connected = True
            self._native_lib = False
            print(f"[Bolt] Connected via serial fallback on {self.device.port}")
            return True
            
        except Exception as e:
            print(f"[Bolt] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Bolt."""
        if self._scope is not None:
            # Native library - no explicit disconnect needed
            self._scope = None
        elif hasattr(self, '_serial') and self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        
        self._connected = False
        self._armed = False
    
    def get_info(self) -> dict[str, Any]:
        """Get Bolt device information."""
        if not self._connected:
            return {"error": "Not connected"}
        
        return {
            "name": "Curious Bolt",
            "capabilities": ["glitch", "logic", "dpa"],
            "clock_period_ns": self.CLOCK_PERIOD_NS,
            "armed": self._armed,
            "current_config": {
                "width_ns": self._glitch_config.width_ns,
                "offset_ns": self._glitch_config.offset_ns,
                "repeat": self._glitch_config.repeat,
            }
        }
    
    # --------------------------------------------------------------------------
    # Glitch Configuration
    # --------------------------------------------------------------------------
    
    def configure_glitch(self, config: GlitchConfig) -> bool:
        """
        Configure glitch parameters.
        
        Args:
            config: GlitchConfig with width_ns, offset_ns, repeat, trigger settings
        """
        if not self._connected:
            return False
        
        self._glitch_config = config
        
        # Convert nanoseconds to clock cycles (8.3ns per cycle)
        repeat_cycles = max(1, int(config.width_ns / self.CLOCK_PERIOD_NS))
        offset_cycles = int(config.offset_ns / self.CLOCK_PERIOD_NS)
        
        if self._scope is not None:
            # Native library
            self._scope.glitch.repeat = repeat_cycles
            self._scope.glitch.ext_offset = offset_cycles
            print(f"[Bolt] Configured: repeat={repeat_cycles} cycles ({config.width_ns:.1f}ns), "
                  f"offset={offset_cycles} cycles ({config.offset_ns:.1f}ns)")
        else:
            # Serial fallback - store for later
            self._repeat_cycles = repeat_cycles
            self._offset_cycles = offset_cycles
            print(f"[Bolt] STUB: configure_glitch - serial protocol not implemented")
        
        return True
    
    def arm(self) -> bool:
        """
        Arm the glitcher to wait for external trigger.
        
        Uses the trigger channel and edge from the current GlitchConfig.
        """
        if not self._connected:
            return False
        
        channel = self._glitch_config.trigger_channel
        if channel is None:
            print("[Bolt] No trigger channel configured - use trigger() for manual")
            return False
        
        edge = self._glitch_config.trigger_edge
        
        if self._scope is not None:
            # Map edge to Bolt constants
            edge_map = {
                TriggerEdge.RISING: 1,   # Scope.RISING_EDGE
                TriggerEdge.FALLING: 0,  # Scope.FALLING_EDGE
                TriggerEdge.EITHER: 2,   # If supported
            }
            bolt_edge = edge_map.get(edge, 0)
            
            # Native library arm
            self._scope.arm(channel, bolt_edge)
            self._armed = True
            print(f"[Bolt] Armed on channel {channel}, {edge.name} edge")
        else:
            print(f"[Bolt] STUB: arm - serial protocol not implemented")
            self._armed = True
        
        return True
    
    def trigger(self) -> bool:
        """Manually trigger a single glitch."""
        if not self._connected:
            return False
        
        if self._scope is not None:
            self._scope.trigger()
            print("[Bolt] Triggered")
        else:
            print("[Bolt] STUB: trigger - serial protocol not implemented")
        
        return True
    
    def disarm(self) -> bool:
        """Disarm the glitcher."""
        if not self._connected:
            return False
        
        # The Bolt library doesn't have explicit disarm - just don't trigger
        self._armed = False
        print("[Bolt] Disarmed")
        return True
    
    # --------------------------------------------------------------------------
    # Glitch Campaign Support
    # --------------------------------------------------------------------------
    
    def run_glitch_sweep(self,
                         width_range: tuple[int, int],  # (min_ns, max_ns)
                         width_step: int,               # Step in ns
                         offset_range: tuple[int, int], # (min_ns, max_ns)  
                         offset_step: int,              # Step in ns
                         attempts_per_setting: int = 10,
                         callback=None) -> list[dict]:
        """
        Run a parameter sweep for glitch attacks.
        
        Args:
            width_range: (min, max) glitch width in nanoseconds
            offset_range: (min, max) offset after trigger in nanoseconds
            attempts_per_setting: Number of glitches at each parameter combo
            callback: Optional function called after each glitch with (config, attempt, result)
            
        Returns:
            List of dicts with parameters and any captured results
        """
        results = []
        
        for width in range(width_range[0], width_range[1] + 1, width_step):
            for offset in range(offset_range[0], offset_range[1] + 1, offset_step):
                config = GlitchConfig(
                    width_ns=width,
                    offset_ns=offset,
                    trigger_channel=self._glitch_config.trigger_channel,
                    trigger_edge=self._glitch_config.trigger_edge
                )
                
                self.configure_glitch(config)
                
                for attempt in range(attempts_per_setting):
                    self.trigger()
                    
                    result = {
                        "width_ns": width,
                        "offset_ns": offset,
                        "attempt": attempt,
                        "timestamp": time.time(),
                    }
                    
                    if callback:
                        callback_result = callback(config, attempt)
                        result["callback_result"] = callback_result
                    
                    results.append(result)
                    
                    # Small delay between glitches
                    time.sleep(0.001)
        
        return results
    
    # --------------------------------------------------------------------------
    # Logic Analyzer (via SUMP protocol)
    # --------------------------------------------------------------------------

    def start_capture(self, channels: list[int], sample_rate_hz: int = 1_000_000) -> bool:
        """
        Start logic analyzer capture.

        Note: The Bolt's logic analyzer is typically accessed via PulseView using
        the SUMP protocol. This method provides basic programmatic access.
        """
        if not self._connected:
            return False

        print(f"[Bolt] STUB: start_capture - use PulseView for logic analysis")
        print(f"  Configure PulseView with: sigrok-cli -d fx2lafw:samplerate={sample_rate_hz}")
        return False

    def capture_logic(
        self,
        sample_rate: int = 1_000_000,
        sample_count: int = 8192,
        channels: int = 8,
        trigger_channel: int | None = None,
        trigger_edge: str = "rising",
        timeout: float = 10.0
    ) -> dict | None:
        """
        Capture logic analyzer data using SUMP protocol.

        The Bolt supports SUMP protocol for logic analyzer access.
        This method uses the shared SUMP implementation.

        Args:
            sample_rate: Sample rate in Hz (max varies by device)
            sample_count: Number of samples to capture
            channels: Number of channels (8 for Bolt)
            trigger_channel: Channel to trigger on (None = immediate)
            trigger_edge: "rising" or "falling"
            timeout: Capture timeout in seconds

        Returns:
            Dict with keys: channels, sample_rate, samples, trigger_position
            Or None on error
        """
        if not self._connected:
            return None

        # For Bolt, we need direct serial access for SUMP mode
        serial_port = None

        if hasattr(self, '_serial') and self._serial:
            serial_port = self._serial
        elif self.device.port:
            # Open a new serial connection for SUMP
            try:
                import serial
                serial_port = serial.Serial(
                    self.device.port,
                    baudrate=115200,
                    timeout=1
                )
            except Exception as e:
                print(f"[Bolt] Failed to open serial for SUMP: {e}")
                return None

        if not serial_port:
            print("[Bolt] No serial port available for SUMP capture")
            return None

        try:
            from .sump import SUMPClient, SUMPConfig

            client = SUMPClient(serial_port, debug=False)

            # Reset and identify
            client.reset()
            success, device_id = client.identify()

            if not success:
                print(f"[Bolt] SUMP device not responding (got: {device_id})")
                return None

            print(f"[Bolt] SUMP device identified: {device_id}")

            # Configure capture
            config = SUMPConfig(
                sample_rate=sample_rate,
                sample_count=sample_count,
                channels=channels,
            )

            # Set trigger if specified
            if trigger_channel is not None and 0 <= trigger_channel < channels:
                config.trigger_mask = 1 << trigger_channel
                if trigger_edge == "rising":
                    config.trigger_value = 1 << trigger_channel
                else:
                    config.trigger_value = 0

            client.configure(config)

            print(f"[Bolt] Starting capture: {sample_rate/1e6:.1f}MHz, {sample_count} samples")
            capture = client.capture(timeout=timeout)

            if capture:
                return {
                    "channels": capture.channels,
                    "sample_rate": capture.sample_rate,
                    "samples": capture.samples,
                    "trigger_position": capture.trigger_position,
                    "raw_data": capture.raw_data,
                }

            return None

        except ImportError:
            print("[Bolt] SUMP module not available")
            return None
        except Exception as e:
            print(f"[Bolt] SUMP capture error: {e}")
            return None
    
    # --------------------------------------------------------------------------
    # Differential Power Analysis
    # --------------------------------------------------------------------------
    
    def capture_power_trace(self, samples: int = 1000) -> Optional[list[float]]:
        """
        Capture power trace from the differential power scope.
        
        Args:
            samples: Number of samples to capture
            
        Returns:
            List of voltage measurements or None on error
        """
        if not self._connected:
            return None
        
        if self._scope is not None:
            # TODO: Implement DPA capture via native library
            print("[Bolt] STUB: capture_power_trace - DPA not yet implemented")
            return None
        
        return None


# Register this backend
register_backend("bolt", BoltBackend)
