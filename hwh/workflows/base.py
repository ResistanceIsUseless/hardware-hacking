"""
Base classes for multi-device workflows.

Workflows coordinate multiple hardware devices to accomplish complex tasks
like glitching while monitoring, or dual-protocol analysis.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class WorkflowResult:
    """Results from workflow execution."""
    status: WorkflowStatus
    duration_seconds: float
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Workflow(ABC):
    """
    Base class for multi-device workflows.

    Workflows define coordinated operations across multiple hardware devices.
    They handle:
    - Device coordination
    - Progress tracking
    - Error handling
    - Result collection
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = WorkflowStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._progress: float = 0.0
        self._status_message: str = ""
        self._progress_callback: Optional[Callable] = None
        self._cancel_event = asyncio.Event()

    @property
    def progress(self) -> float:
        """Get progress percentage (0.0 to 100.0)."""
        return self._progress

    @property
    def status_message(self) -> str:
        """Get current status message."""
        return self._status_message

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self._progress_callback = callback

    def update_progress(self, progress: float, message: str = ""):
        """
        Update workflow progress.

        Args:
            progress: Progress percentage (0.0 to 100.0)
            message: Status message
        """
        self._progress = min(max(progress, 0.0), 100.0)
        self._status_message = message

        if self._progress_callback:
            self._progress_callback(self._progress, message)

    async def cancel(self):
        """Request workflow cancellation."""
        self._cancel_event.set()
        self.status = WorkflowStatus.CANCELLED
        self.update_progress(self._progress, "Cancelling...")

    @property
    def is_cancelled(self) -> bool:
        """Check if workflow has been cancelled."""
        return self._cancel_event.is_set()

    @abstractmethod
    async def setup(self, device_pool) -> bool:
        """
        Setup workflow - verify devices and prepare.

        Args:
            device_pool: DevicePool instance with available devices

        Returns:
            True if setup succeeded
        """
        pass

    @abstractmethod
    async def execute(self, device_pool) -> WorkflowResult:
        """
        Execute the workflow.

        Args:
            device_pool: DevicePool instance

        Returns:
            WorkflowResult with outcome
        """
        pass

    @abstractmethod
    async def cleanup(self, device_pool):
        """
        Cleanup after workflow (success or failure).

        Args:
            device_pool: DevicePool instance
        """
        pass

    async def run(self, device_pool) -> WorkflowResult:
        """
        Run the complete workflow (setup -> execute -> cleanup).

        Args:
            device_pool: DevicePool instance

        Returns:
            WorkflowResult
        """
        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now()
        self.update_progress(0.0, "Starting workflow...")

        errors = []

        try:
            # Setup
            self.update_progress(5.0, "Setting up...")
            if not await self.setup(device_pool):
                raise RuntimeError("Workflow setup failed")

            # Execute
            self.update_progress(10.0, "Executing...")
            result = await self.execute(device_pool)

            # Mark complete
            self.status = WorkflowStatus.COMPLETED
            self.update_progress(100.0, "Completed")

            return result

        except asyncio.CancelledError:
            self.status = WorkflowStatus.CANCELLED
            errors.append("Workflow cancelled by user")
            raise

        except Exception as e:
            self.status = WorkflowStatus.FAILED
            error_msg = f"Workflow failed: {e}"
            errors.append(error_msg)
            self.update_progress(self._progress, error_msg)

            return WorkflowResult(
                status=WorkflowStatus.FAILED,
                duration_seconds=(datetime.now() - self.start_time).total_seconds(),
                errors=errors
            )

        finally:
            # Always cleanup
            self.update_progress(95.0, "Cleaning up...")
            await self.cleanup(device_pool)

            self.end_time = datetime.now()


class ParameterSweepWorkflow(Workflow):
    """
    Base class for workflows that sweep parameters.

    Useful for glitch campaigns, optimization, etc.
    """

    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self.total_iterations = 0
        self.current_iteration = 0
        self.successes: List[Dict] = []

    def calculate_total_iterations(self, ranges: Dict[str, range]) -> int:
        """
        Calculate total iterations from parameter ranges.

        Args:
            ranges: Dict mapping parameter name to range object

        Returns:
            Total number of iterations
        """
        total = 1
        for param_range in ranges.values():
            total *= len(param_range)
        return total

    def update_iteration(self, iteration: int):
        """Update current iteration and progress."""
        self.current_iteration = iteration

        if self.total_iterations > 0:
            progress = (iteration / self.total_iterations) * 90.0  # Reserve 10% for completion
            self.update_progress(
                10.0 + progress,
                f"Iteration {iteration}/{self.total_iterations}"
            )

    def record_success(self, parameters: Dict, details: Dict):
        """Record a successful parameter combination."""
        self.successes.append({
            'iteration': self.current_iteration,
            'parameters': parameters.copy(),
            'details': details.copy(),
            'timestamp': datetime.now()
        })


class MonitoringMixin:
    """
    Mixin for workflows that need to monitor device output.
    """

    def __init__(self):
        self._monitor_buffer: List[bytes] = []
        self._monitor_running = False

    async def start_monitoring(self, device_backend, interval_ms: int = 100):
        """
        Start background monitoring of device output.

        Args:
            device_backend: Backend to monitor
            interval_ms: Polling interval in milliseconds
        """
        self._monitor_running = True
        self._monitor_buffer.clear()

        async def monitor_loop():
            while self._monitor_running:
                try:
                    data = device_backend.uart_read(length=4096, timeout_ms=interval_ms)
                    if data:
                        self._monitor_buffer.append(data)
                except:
                    pass  # Ignore read errors
                await asyncio.sleep(interval_ms / 1000.0)

        self._monitor_task = asyncio.create_task(monitor_loop())

    async def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitor_running = False
        if hasattr(self, '_monitor_task'):
            await self._monitor_task

    def get_monitor_data(self, clear: bool = True) -> bytes:
        """
        Get monitored data.

        Args:
            clear: Clear buffer after reading

        Returns:
            Concatenated monitored data
        """
        data = b''.join(self._monitor_buffer)
        if clear:
            self._monitor_buffer.clear()
        return data

    def check_monitor_for_pattern(self, pattern: bytes) -> bool:
        """
        Check if monitored data contains a pattern.

        Args:
            pattern: Byte pattern to search for

        Returns:
            True if pattern found
        """
        data = self.get_monitor_data(clear=False)
        return pattern in data
