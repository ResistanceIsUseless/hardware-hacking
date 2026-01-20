"""
Condition Monitoring System

Pattern-based automation for glitching campaigns.
Monitors serial output and triggers actions when patterns are detected.

Inspired by glitch-o-bolt by 0xRoM (https://rossmarks.uk/git/0xRoM/glitch-o-bolt)
"""

import asyncio
import re
from typing import List, Tuple, Callable, Optional
from dataclasses import dataclass


@dataclass
class Condition:
    """
    Represents an automation condition

    Args:
        name: Short descriptive name (max 8 chars for UI display)
        enabled: Whether this condition is active
        pattern: Regex pattern to match in serial output
        action: Function to call when pattern matches
        description: Optional longer description
    """
    name: str
    enabled: bool
    pattern: str
    action: Callable
    description: str = ""


class ConditionMonitor:
    """
    Monitors serial buffer for pattern matches and triggers automation

    Example:
        >>> def stop_on_flag():
        ...     print("Flag found!")
        ...     glitcher.stop()

        >>> monitor = ConditionMonitor()
        >>> monitor.add_condition("Flag", True, r"ctf\{.*?\}", stop_on_flag)
        >>> monitor.check_buffer("Here's your flag: ctf{test123}")
        # Calls stop_on_flag()
    """

    def __init__(self, buffer_size: int = 4096):
        """
        Args:
            buffer_size: Maximum size of serial buffer to keep
        """
        self.conditions: List[Condition] = []
        self.buffer = ""
        self.buffer_size = buffer_size
        self._lock = asyncio.Lock()

    def add_condition(
        self,
        name: str,
        enabled: bool,
        pattern: str,
        action: Callable,
        description: str = ""
    ) -> None:
        """Add a condition to monitor for"""
        condition = Condition(
            name=name,
            enabled=enabled,
            pattern=pattern,
            action=action,
            description=description
        )
        self.conditions.append(condition)

    def remove_condition(self, name: str) -> bool:
        """Remove a condition by name. Returns True if found and removed."""
        for i, cond in enumerate(self.conditions):
            if cond.name == name:
                self.conditions.pop(i)
                return True
        return False

    def enable_condition(self, name: str) -> bool:
        """Enable a condition by name. Returns True if found."""
        for cond in self.conditions:
            if cond.name == name:
                cond.enabled = True
                return True
        return False

    def disable_condition(self, name: str) -> bool:
        """Disable a condition by name. Returns True if found."""
        for cond in self.conditions:
            if cond.name == name:
                cond.enabled = False
                return True
        return False

    async def append_data(self, data: str) -> None:
        """Thread-safe append to serial buffer"""
        async with self._lock:
            self.buffer += data

            # Trim buffer if too large
            if len(self.buffer) > self.buffer_size:
                self.buffer = self.buffer[-self.buffer_size:]

    def check_buffer(self, debug: bool = False) -> Optional[Tuple[str, Callable]]:
        """
        Check buffer for pattern matches

        Returns:
            (condition_name, action) tuple if match found, None otherwise
        """
        for cond in self.conditions:
            if not cond.enabled:
                continue

            if re.search(cond.pattern, self.buffer):
                if debug:
                    print(f"[CONDITION] Matched: {cond.name} (pattern: {cond.pattern})")
                return (cond.name, cond.action)

        return None

    async def monitor_loop(
        self,
        serial_stream,
        check_interval: float = 0.1,
        debug: bool = False
    ) -> None:
        """
        Continuously monitor serial stream for conditions

        Args:
            serial_stream: Async iterator yielding serial data
            check_interval: How often to check buffer (seconds)
            debug: Enable debug logging
        """
        while True:
            try:
                # Get new data from serial stream
                try:
                    data = await asyncio.wait_for(
                        serial_stream.__anext__(),
                        timeout=check_interval
                    )
                    await self.append_data(data)
                except asyncio.TimeoutError:
                    pass  # No data, that's OK

                # Check for pattern matches
                result = self.check_buffer(debug=debug)
                if result:
                    name, action = result
                    if debug:
                        print(f"[CONDITION] Executing action for: {name}")

                    # Execute action (may be sync or async)
                    if asyncio.iscoroutinefunction(action):
                        await action()
                    else:
                        action()

            except Exception as e:
                if debug:
                    print(f"[CONDITION] Error: {e}")
                await asyncio.sleep(check_interval)

    def get_buffer_tail(self, lines: int = 10) -> str:
        """Get the last N lines from the buffer for display"""
        buffer_lines = self.buffer.split('\n')
        return '\n'.join(buffer_lines[-lines:])

    def clear_buffer(self) -> None:
        """Clear the serial buffer"""
        self.buffer = ""

    def get_enabled_conditions(self) -> List[Condition]:
        """Get list of currently enabled conditions"""
        return [c for c in self.conditions if c.enabled]

    def __repr__(self) -> str:
        enabled = sum(1 for c in self.conditions if c.enabled)
        return f"ConditionMonitor({len(self.conditions)} conditions, {enabled} enabled)"


# Helper functions for common condition patterns

def pattern_flag(prefix: str = "ctf") -> str:
    """Regex pattern for CTF flags like ctf{...}"""
    return rf"{prefix}\{{[^}}]+\}}"


def pattern_success_messages() -> List[str]:
    """Common success message patterns"""
    return [
        r"success",
        r"passed",
        r"correct",
        r"flag",
        r"win",
        r"pwned"
    ]


def pattern_failure_messages() -> List[str]:
    """Common failure message patterns"""
    return [
        r"fail",
        r"error",
        r"wrong",
        r"crash",
        r"reset"
    ]


# Example usage in doctest
if __name__ == "__main__":
    import doctest
    doctest.testmod()
