"""
Glitch + Monitor Workflow

Use one device (e.g., Curious Bolt) to inject faults while another device
(e.g., Bus Pirate) monitors UART output for success indicators.

Classic use case: Voltage glitching to bypass authentication or RDP protection
while monitoring serial console for successful exploitation.
"""

import asyncio
from typing import Optional, Dict, Callable
from dataclasses import dataclass

from .base import ParameterSweepWorkflow, MonitoringMixin, WorkflowResult, WorkflowStatus
from ..tui.device_pool import DeviceRole
from ..backends import GlitchBackend, BusBackend, GlitchConfig


@dataclass
class GlitchParameters:
    """Glitch parameter sweep configuration."""
    width_min: int
    width_max: int
    width_step: int
    offset_min: int
    offset_max: int
    offset_step: int
    attempts_per_setting: int = 3


@dataclass
class SuccessCriteria:
    """Criteria for detecting successful glitch."""
    patterns: list[bytes]  # Byte patterns that indicate success
    timeout_ms: int = 1000  # Timeout to wait for pattern
    reset_command: Optional[str] = None  # Command to reset target


class GlitchMonitorWorkflow(ParameterSweepWorkflow, MonitoringMixin):
    """
    Glitch + Monitor workflow.

    Coordinates a glitcher device (Bolt, FaultyCat) with a monitoring device
    (Bus Pirate) to detect successful fault injection.
    """

    def __init__(
        self,
        glitch_params: GlitchParameters,
        success_criteria: SuccessCriteria,
        reset_callback: Optional[Callable] = None
    ):
        ParameterSweepWorkflow.__init__(
            self,
            name="Glitch + Monitor",
            description="Voltage glitching with UART monitoring"
        )
        MonitoringMixin.__init__(self)

        self.glitch_params = glitch_params
        self.success_criteria = success_criteria
        self.reset_callback = reset_callback

        # Device references (set during setup)
        self.glitcher_id: Optional[str] = None
        self.monitor_id: Optional[str] = None

    async def setup(self, device_pool) -> bool:
        """Setup glitcher and monitor devices."""
        self.update_progress(0.0, "Setting up devices...")

        # Find glitcher
        glitchers = device_pool.get_devices_by_role(DeviceRole.GLITCHER)
        if not glitchers:
            # Try to find a device with glitch capability
            glitchers = device_pool.get_devices_by_capability("voltage_glitch")
            if not glitchers:
                glitchers = device_pool.get_devices_by_capability("emfi")

        if not glitchers:
            self.update_progress(0.0, "ERROR: No glitcher device found")
            return False

        self.glitcher_id = glitchers[0]
        device_pool.assign_role(self.glitcher_id, DeviceRole.GLITCHER)

        # Find monitor
        monitors = device_pool.get_devices_by_role(DeviceRole.MONITOR)
        if not monitors:
            # Find device with UART capability
            monitors = device_pool.get_devices_by_capability("uart")

        if not monitors:
            self.update_progress(0.0, "ERROR: No monitor device found")
            return False

        self.monitor_id = monitors[0]
        device_pool.assign_role(self.monitor_id, DeviceRole.MONITOR)

        # Connect devices
        if not await device_pool.connect(self.glitcher_id):
            self.update_progress(0.0, "ERROR: Failed to connect glitcher")
            return False

        if not await device_pool.connect(self.monitor_id):
            self.update_progress(0.0, "ERROR: Failed to connect monitor")
            return False

        # Calculate total iterations
        width_range = range(
            self.glitch_params.width_min,
            self.glitch_params.width_max + 1,
            self.glitch_params.width_step
        )
        offset_range = range(
            self.glitch_params.offset_min,
            self.glitch_params.offset_max + 1,
            self.glitch_params.offset_step
        )

        self.total_iterations = (
            len(width_range) *
            len(offset_range) *
            self.glitch_params.attempts_per_setting
        )

        self.update_progress(5.0, f"Setup complete. {self.total_iterations} iterations planned.")
        return True

    async def execute(self, device_pool) -> WorkflowResult:
        """Execute glitch sweep with monitoring."""
        # Get backends
        glitcher_backend = device_pool.get_backend(self.glitcher_id)
        monitor_backend = device_pool.get_backend(self.monitor_id)

        if not isinstance(glitcher_backend, GlitchBackend):
            raise RuntimeError("Glitcher device doesn't support glitching")

        if not isinstance(monitor_backend, BusBackend):
            raise RuntimeError("Monitor device doesn't support UART")

        # Start monitoring UART
        self.update_progress(10.0, "Starting UART monitor...")
        await self.start_monitoring(monitor_backend, interval_ms=50)

        iteration = 0

        try:
            # Sweep parameters
            for width in range(
                self.glitch_params.width_min,
                self.glitch_params.width_max + 1,
                self.glitch_params.width_step
            ):
                for offset in range(
                    self.glitch_params.offset_min,
                    self.glitch_params.offset_max + 1,
                    self.glitch_params.offset_step
                ):
                    # Check for cancellation
                    if self.is_cancelled:
                        break

                    # Configure glitch
                    config = GlitchConfig(width_ns=width, offset_ns=offset)
                    glitcher_backend.configure_glitch(config)

                    # Multiple attempts at this parameter setting
                    for attempt in range(self.glitch_params.attempts_per_setting):
                        iteration += 1
                        self.update_iteration(iteration)

                        # Clear monitor buffer
                        self.get_monitor_data(clear=True)

                        # Reset target if callback provided
                        if self.reset_callback:
                            await self.reset_callback()
                            await asyncio.sleep(0.1)

                        # Trigger glitch
                        glitcher_backend.trigger()

                        # Wait for response and check for success
                        await asyncio.sleep(self.success_criteria.timeout_ms / 1000.0)

                        # Check if any success pattern appeared
                        success = False
                        for pattern in self.success_criteria.patterns:
                            if self.check_monitor_for_pattern(pattern):
                                success = True
                                break

                        if success:
                            self.record_success(
                                parameters={'width_ns': width, 'offset_ns': offset, 'attempt': attempt},
                                details={
                                    'output': self.get_monitor_data(clear=False).decode(errors='ignore')
                                }
                            )
                            self.update_progress(
                                10.0 + ((iteration / self.total_iterations) * 85.0),
                                f"SUCCESS! width={width}ns, offset={offset}ns (Total: {len(self.successes)})"
                            )

                if self.is_cancelled:
                    break

        finally:
            # Stop monitoring
            await self.stop_monitoring()

        # Build result
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0.0

        return WorkflowResult(
            status=WorkflowStatus.COMPLETED if not self.is_cancelled else WorkflowStatus.CANCELLED,
            duration_seconds=duration,
            results={
                'total_iterations': iteration,
                'successes': self.successes,
                'success_count': len(self.successes),
                'success_rate': len(self.successes) / iteration if iteration > 0 else 0.0
            },
            metadata={
                'glitch_params': {
                    'width_range': (self.glitch_params.width_min, self.glitch_params.width_max, self.glitch_params.width_step),
                    'offset_range': (self.glitch_params.offset_min, self.glitch_params.offset_max, self.glitch_params.offset_step),
                    'attempts_per_setting': self.glitch_params.attempts_per_setting
                }
            }
        )

    async def cleanup(self, device_pool):
        """Cleanup after workflow."""
        # Stop monitoring if still running
        if self._monitor_running:
            await self.stop_monitoring()

        # Disarm glitcher
        if self.glitcher_id:
            glitcher_backend = device_pool.get_backend(self.glitcher_id)
            if isinstance(glitcher_backend, GlitchBackend):
                try:
                    glitcher_backend.disarm()
                except:
                    pass

        self.update_progress(100.0, "Cleanup complete")


# Convenience function
def create_glitch_monitor_workflow(
    width_range: tuple[int, int, int],
    offset_range: tuple[int, int, int],
    success_patterns: list[bytes],
    attempts_per_setting: int = 3,
    timeout_ms: int = 1000,
    reset_callback: Optional[Callable] = None
) -> GlitchMonitorWorkflow:
    """
    Create a glitch + monitor workflow with simplified parameters.

    Args:
        width_range: (min, max, step) for glitch width in nanoseconds
        offset_range: (min, max, step) for glitch offset in nanoseconds
        success_patterns: List of byte patterns indicating success
        attempts_per_setting: Number of glitches per parameter combination
        timeout_ms: Timeout to wait for success pattern
        reset_callback: Optional function to reset target between attempts

    Returns:
        GlitchMonitorWorkflow instance

    Example:
        workflow = create_glitch_monitor_workflow(
            width_range=(50, 500, 25),
            offset_range=(1000, 10000, 500),
            success_patterns=[b'# ', b'root@'],
            attempts_per_setting=5
        )
    """
    glitch_params = GlitchParameters(
        width_min=width_range[0],
        width_max=width_range[1],
        width_step=width_range[2],
        offset_min=offset_range[0],
        offset_max=offset_range[1],
        offset_step=offset_range[2],
        attempts_per_setting=attempts_per_setting
    )

    success_criteria = SuccessCriteria(
        patterns=success_patterns,
        timeout_ms=timeout_ms
    )

    return GlitchMonitorWorkflow(glitch_params, success_criteria, reset_callback)
