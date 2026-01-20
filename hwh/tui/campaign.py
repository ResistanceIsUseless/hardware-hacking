"""
Glitch Campaign Engine

Coordinates glitching hardware, serial monitoring, and condition-based automation.

Based on patterns from glitch-o-bolt by 0xRoM
"""

import asyncio
import serial
import time
from typing import Optional, Callable
from dataclasses import dataclass

from .config import GlitchConfig, GlitchParams
from .conditions import ConditionMonitor
from ..backends import GlitchBackend


@dataclass
class CampaignStats:
    """Statistics for a glitching campaign"""
    glitches_sent: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    success: bool = False
    success_params: Optional[GlitchParams] = None

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time"""
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def glitches_per_second(self) -> float:
        """Calculate glitch rate"""
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0.0
        return self.glitches_sent / elapsed


class GlitchCampaign:
    """
    Automated glitching campaign with condition monitoring

    Example:
        >>> from hwh import get_backend, detect
        >>> from hwh.tui import GlitchCampaign
        >>> from hwh.tui.config import load_config_file

        >>> # Detect hardware
        >>> devices = detect()
        >>> bolt = get_backend(devices['bolt'])

        >>> # Load config
        >>> config = load_config_file('configs/challenge2.py')

        >>> # Run campaign
        >>> campaign = GlitchCampaign(bolt, config)
        >>> await campaign.run()
    """

    def __init__(
        self,
        glitch_backend: GlitchBackend,
        config: GlitchConfig,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            glitch_backend: Hardware backend (e.g., BoltBackend)
            config: Campaign configuration
            log_callback: Optional function to call with log messages
        """
        self.glitch_backend = glitch_backend
        self.config = config
        self.log_callback = log_callback or print

        self.condition_monitor = ConditionMonitor()
        self.stats = CampaignStats()

        self._serial = None
        self._running = False
        self._continuous = False

    def log(self, message: str) -> None:
        """Log a message"""
        self.log_callback(f"[{time.strftime('%H:%M:%S')}] {message}")

    async def setup(self) -> None:
        """Initialize hardware and serial connection"""
        self.log("Setting up campaign...")

        # Connect to glitch backend
        if not self.glitch_backend._device:
            self.glitch_backend.connect()
            self.log(f"Connected to {self.glitch_backend._device.device_type}")

        # Configure glitch parameters
        repeat, offset = self.config.glitch.to_bolt_cycles()
        self.log(f"Glitch params: {repeat} cycles (~{repeat*8.3:.0f}ns), offset {offset}")

        # Open serial connection
        try:
            self._serial = serial.Serial(
                port=self.config.serial.port,
                baudrate=self.config.serial.baudrate,
                timeout=self.config.serial.timeout
            )
            self.log(f"Serial opened: {self.config.serial.port} @ {self.config.serial.baudrate}")
        except Exception as e:
            self.log(f"Warning: Could not open serial: {e}")
            self._serial = None

        # Setup conditions
        for cond in self.config.conditions:
            func = self.config.custom_functions.get(cond['function'])
            if func:
                self.condition_monitor.add_condition(
                    name=cond['name'],
                    enabled=cond['enabled'],
                    pattern=cond['pattern'],
                    action=func
                )
                self.log(f"Condition: {cond['name']} → {cond['function']}()")

        self._running = True

    async def teardown(self) -> None:
        """Clean up resources"""
        self._running = False

        if self._serial and self._serial.is_open:
            self._serial.close()
            self.log("Serial closed")

        if self.glitch_backend._device:
            self.glitch_backend.disconnect()
            self.log("Glitch backend disconnected")

    async def trigger_single_glitch(self) -> None:
        """Trigger a single glitch with current parameters"""
        # Configure glitch backend
        from ..backends import GlitchConfig as BackendGlitchConfig
        glitch_cfg = BackendGlitchConfig(
            width_ns=self.config.glitch.width_ns,
            offset_ns=self.config.glitch.offset_ns,
            repeat=1
        )

        self.glitch_backend.configure_glitch(glitch_cfg)
        self.glitch_backend.trigger()

        self.stats.glitches_sent += 1

    async def run_continuous(self, interval_ms: float = 10.0) -> None:
        """
        Run continuous glitching

        Args:
            interval_ms: Delay between glitches in milliseconds
        """
        self._continuous = True
        self.stats.start_time = time.time()

        self.log("Starting continuous glitching...")

        while self._running and self._continuous:
            await self.trigger_single_glitch()
            await asyncio.sleep(interval_ms / 1000.0)

        self.stats.end_time = time.time()
        self.log(f"Stopped. Sent {self.stats.glitches_sent} glitches in {self.stats.elapsed_seconds:.1f}s")

    def stop_glitching(self) -> None:
        """Stop continuous glitching"""
        self._continuous = False
        self.log("Stopping glitching...")

    async def read_serial_loop(self) -> None:
        """Background task to read serial data and feed condition monitor"""
        if not self._serial:
            return

        buffer = ""

        while self._running:
            try:
                if self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    decoded = data.decode('utf-8', errors='ignore')

                    # Update condition monitor
                    await self.condition_monitor.append_data(decoded)

                    # Log to callback
                    for char in decoded:
                        buffer += char
                        if char == '\n':
                            self.log(f"RX: {buffer.strip()}")
                            buffer = ""

                await asyncio.sleep(0.01)

            except Exception as e:
                self.log(f"Serial read error: {e}")
                await asyncio.sleep(0.1)

    async def monitor_conditions_loop(self) -> None:
        """Background task to check for condition matches"""
        while self._running:
            result = self.condition_monitor.check_buffer(debug=False)

            if result:
                name, action = result
                self.log(f"✓ Condition matched: {name}")

                # Execute action
                try:
                    if asyncio.iscoroutinefunction(action):
                        await action()
                    else:
                        action()
                except Exception as e:
                    self.log(f"Error executing {name}: {e}")

            await asyncio.sleep(0.1)

    async def run(self) -> CampaignStats:
        """
        Run the complete glitching campaign

        Returns:
            Campaign statistics
        """
        await self.setup()

        # Start background tasks
        tasks = [
            asyncio.create_task(self.read_serial_loop()),
            asyncio.create_task(self.monitor_conditions_loop()),
        ]

        # Wait for completion or cancellation
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.log("Campaign cancelled")
        finally:
            await self.teardown()

        return self.stats


# Helper function for simple campaign execution
async def run_campaign(
    glitch_backend: GlitchBackend,
    config_path: str,
    log_callback: Optional[Callable[[str], None]] = None
) -> CampaignStats:
    """
    Convenience function to run a campaign from a config file

    Args:
        glitch_backend: Glitching hardware backend
        config_path: Path to config file
        log_callback: Optional logging function

    Returns:
        Campaign statistics
    """
    from .config import load_config_file

    config = load_config_file(config_path)
    campaign = GlitchCampaign(glitch_backend, config, log_callback)

    return await campaign.run()
