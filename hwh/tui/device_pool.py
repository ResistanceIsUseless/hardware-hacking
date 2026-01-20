"""
Device Pool - Multi-device coordination and management.

Manages multiple hardware devices simultaneously, allowing coordinated operations
like glitching with one device while monitoring with another.
"""

import asyncio
from typing import Dict, Optional, List, Set, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime

from ..detect import DeviceInfo, detect
from ..backends import Backend, get_backend, BusBackend, GlitchBackend, DebugBackend


class DeviceRole(Enum):
    """Roles that devices can play in workflows."""
    PRIMARY = auto()       # Main device for current operation
    MONITOR = auto()       # Monitoring/logging device
    GLITCHER = auto()     # Fault injection device
    FLASHER = auto()      # Programming/flash operations
    DEBUGGER = auto()     # Debug probe
    AUXILIARY = auto()    # Supporting role


@dataclass
class DeviceState:
    """Runtime state of a device in the pool."""
    device_info: DeviceInfo
    backend: Optional[Backend] = None
    role: DeviceRole = DeviceRole.AUXILIARY
    connected: bool = False
    active: bool = False
    last_activity: Optional[datetime] = None
    error_count: int = 0
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class DeviceRecommendation:
    """Recommendation for device selection."""
    device_id: str
    device_info: DeviceInfo
    confidence: float  # 0.0 to 1.0
    reason: str
    suggested_role: DeviceRole


class DevicePool:
    """
    Manages multiple hardware devices simultaneously.

    Features:
    - Auto-detect devices on initialization
    - Assign roles for multi-device workflows
    - Coordinate async operations across devices
    - Track device state and health
    - Smart device selection based on capabilities
    """

    def __init__(self):
        self.devices: Dict[str, DeviceState] = {}
        self.primary_device: Optional[str] = None
        self._locks: Dict[str, asyncio.Lock] = {}
        self._history: List[Dict] = []

    async def scan_devices(self, identify_unknown: bool = True) -> List[str]:
        """
        Scan for connected devices and add them to the pool.

        Args:
            identify_unknown: Attempt to identify unknown RP2040 devices

        Returns:
            List of device IDs that were found
        """
        detected = detect(identify_unknown=identify_unknown)
        found_ids = []

        for device_id, device_info in detected.items():
            if device_id not in self.devices:
                # New device - add to pool
                state = DeviceState(
                    device_info=device_info,
                    role=DeviceRole.AUXILIARY
                )
                self.devices[device_id] = state
                self._locks[device_id] = asyncio.Lock()
                found_ids.append(device_id)

                # Auto-connect if this is the only device
                if len(self.devices) == 1:
                    await self.connect(device_id)
                    self.primary_device = device_id
                    state.role = DeviceRole.PRIMARY

        return found_ids

    async def connect(self, device_id: str) -> bool:
        """
        Connect to a device in the pool.

        Args:
            device_id: Device identifier

        Returns:
            True if connection succeeded
        """
        if device_id not in self.devices:
            return False

        state = self.devices[device_id]

        if state.connected:
            return True

        try:
            # Create backend if not already created
            if not state.backend:
                state.backend = get_backend(state.device_info)

                if not state.backend:
                    return False

            # Connect
            state.backend.connect()
            state.connected = True
            state.last_activity = datetime.now()
            state.error_count = 0

            return True

        except Exception as e:
            state.error_count += 1
            state.metadata['last_error'] = str(e)
            return False

    async def disconnect(self, device_id: str) -> bool:
        """
        Disconnect from a device.

        Args:
            device_id: Device identifier

        Returns:
            True if disconnect succeeded
        """
        if device_id not in self.devices:
            return False

        state = self.devices[device_id]

        if not state.connected:
            return True

        try:
            if state.backend:
                state.backend.disconnect()

            state.connected = False
            state.active = False

            return True

        except Exception as e:
            state.metadata['last_error'] = str(e)
            return False

    async def disconnect_all(self):
        """Disconnect all devices in the pool."""
        for device_id in list(self.devices.keys()):
            await self.disconnect(device_id)

    def assign_role(self, device_id: str, role: DeviceRole) -> bool:
        """
        Assign a role to a device for workflow coordination.

        Args:
            device_id: Device identifier
            role: Role to assign

        Returns:
            True if role was assigned
        """
        if device_id not in self.devices:
            return False

        state = self.devices[device_id]
        old_role = state.role
        state.role = role

        # If assigning PRIMARY, clear any other primary
        if role == DeviceRole.PRIMARY:
            for other_id, other_state in self.devices.items():
                if other_id != device_id and other_state.role == DeviceRole.PRIMARY:
                    other_state.role = DeviceRole.AUXILIARY

            self.primary_device = device_id

        # Log role change
        self._history.append({
            'timestamp': datetime.now(),
            'event': 'role_change',
            'device_id': device_id,
            'old_role': old_role,
            'new_role': role
        })

        return True

    def get_device(self, device_id: str) -> Optional[DeviceState]:
        """Get device state by ID."""
        return self.devices.get(device_id)

    def get_backend(self, device_id: str) -> Optional[Backend]:
        """Get backend instance for a device."""
        state = self.devices.get(device_id)
        return state.backend if state else None

    def get_devices_by_role(self, role: DeviceRole) -> List[str]:
        """Get all device IDs with a specific role."""
        return [
            device_id
            for device_id, state in self.devices.items()
            if state.role == role
        ]

    def get_devices_by_capability(self, capability: str) -> List[str]:
        """Get all device IDs with a specific capability."""
        return [
            device_id
            for device_id, state in self.devices.items()
            if capability in state.device_info.capabilities
        ]

    def get_primary(self) -> Optional[DeviceState]:
        """Get the primary device."""
        if self.primary_device:
            return self.devices.get(self.primary_device)
        return None

    async def with_device(self, device_id: str) -> asyncio.Lock:
        """
        Get an async lock for exclusive access to a device.

        Usage:
            async with pool.with_device("bolt") as lock:
                # Perform operations on device
                backend = pool.get_backend("bolt")
                backend.do_something()
        """
        if device_id not in self._locks:
            self._locks[device_id] = asyncio.Lock()

        return self._locks[device_id]

    def recommend_for_task(self, task_description: str) -> List[DeviceRecommendation]:
        """
        Recommend devices for a task based on capabilities.

        Args:
            task_description: Description of task (e.g., "glitch STM32", "dump SPI flash")

        Returns:
            List of recommendations sorted by confidence (highest first)
        """
        recommendations = []
        task_lower = task_description.lower()

        for device_id, state in self.devices.items():
            confidence = 0.0
            reasons = []
            suggested_role = DeviceRole.AUXILIARY

            caps = [c.lower() for c in state.device_info.capabilities]

            # Glitching tasks
            if any(word in task_lower for word in ['glitch', 'fault', 'injection']):
                if any(c in caps for c in ['voltage_glitch', 'glitch', 'emfi']):
                    confidence += 0.8
                    reasons.append("Supports fault injection")
                    suggested_role = DeviceRole.GLITCHER

            # Debugging tasks
            if any(word in task_lower for word in ['debug', 'swd', 'jtag', 'dump firmware']):
                if any(c in caps for c in ['swd', 'jtag', 'debug']):
                    confidence += 0.9
                    reasons.append("Supports debugging protocols")
                    suggested_role = DeviceRole.DEBUGGER

            # Flash operations
            if any(word in task_lower for word in ['flash', 'spi', 'dump', 'read']):
                if 'spi' in caps:
                    confidence += 0.7
                    reasons.append("Supports SPI")
                    suggested_role = DeviceRole.FLASHER

            # UART monitoring
            if any(word in task_lower for word in ['uart', 'serial', 'monitor', 'console']):
                if 'uart' in caps:
                    confidence += 0.6
                    reasons.append("Supports UART")
                    suggested_role = DeviceRole.MONITOR

            # I2C operations
            if 'i2c' in task_lower:
                if 'i2c' in caps:
                    confidence += 0.7
                    reasons.append("Supports I2C")

            # Connected devices get bonus
            if state.connected:
                confidence += 0.1
                reasons.append("Already connected")

            # Recently used devices get slight bonus
            if state.last_activity:
                time_delta = (datetime.now() - state.last_activity).seconds
                if time_delta < 300:  # Used in last 5 minutes
                    confidence += 0.05
                    reasons.append("Recently used")

            # Penalize devices with recent errors
            if state.error_count > 0:
                confidence -= 0.1 * state.error_count
                reasons.append(f"{state.error_count} recent errors")

            if confidence > 0:
                recommendations.append(DeviceRecommendation(
                    device_id=device_id,
                    device_info=state.device_info,
                    confidence=min(confidence, 1.0),
                    reason=", ".join(reasons),
                    suggested_role=suggested_role
                ))

        # Sort by confidence descending
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        return recommendations

    async def auto_select(self, task_description: str) -> Optional[str]:
        """
        Automatically select and connect to the best device for a task.

        Args:
            task_description: Description of task

        Returns:
            Device ID of selected device, or None if no suitable device
        """
        recommendations = self.recommend_for_task(task_description)

        if not recommendations:
            return None

        # Try to connect to the top recommendation
        best = recommendations[0]

        if await self.connect(best.device_id):
            # Assign suggested role
            self.assign_role(best.device_id, best.suggested_role)
            return best.device_id

        # If top choice failed, try the next one
        if len(recommendations) > 1:
            second = recommendations[1]
            if await self.connect(second.device_id):
                self.assign_role(second.device_id, second.suggested_role)
                return second.device_id

        return None

    def get_status(self) -> Dict:
        """
        Get overall pool status.

        Returns:
            Dict with pool statistics and device states
        """
        total = len(self.devices)
        connected = sum(1 for s in self.devices.values() if s.connected)
        active = sum(1 for s in self.devices.values() if s.active)
        errors = sum(s.error_count for s in self.devices.values())

        return {
            'total_devices': total,
            'connected': connected,
            'active': active,
            'total_errors': errors,
            'primary_device': self.primary_device,
            'devices': {
                device_id: {
                    'name': state.device_info.name,
                    'type': state.device_info.device_type,
                    'role': state.role.name,
                    'connected': state.connected,
                    'active': state.active,
                    'capabilities': state.device_info.capabilities,
                    'errors': state.error_count,
                }
                for device_id, state in self.devices.items()
            }
        }

    async def coordinate(self, workflow_func: Callable, device_roles: Dict[DeviceRole, str]):
        """
        Coordinate a multi-device workflow.

        Args:
            workflow_func: Async function that performs the workflow
            device_roles: Mapping of roles to device IDs

        Example:
            await pool.coordinate(
                glitch_and_monitor_workflow,
                {
                    DeviceRole.GLITCHER: "bolt",
                    DeviceRole.MONITOR: "buspirate"
                }
            )
        """
        # Mark devices as active
        for role, device_id in device_roles.items():
            if device_id in self.devices:
                self.devices[device_id].active = True
                self.devices[device_id].last_activity = datetime.now()

        try:
            # Execute workflow
            await workflow_func(self, device_roles)
        finally:
            # Mark devices as inactive
            for device_id in device_roles.values():
                if device_id in self.devices:
                    self.devices[device_id].active = False


# Convenience function for getting a singleton pool
_global_pool: Optional[DevicePool] = None


def get_global_pool() -> DevicePool:
    """Get or create the global device pool instance."""
    global _global_pool
    if _global_pool is None:
        _global_pool = DevicePool()
    return _global_pool
