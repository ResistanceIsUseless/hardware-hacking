"""
UART Protocol Automation - Smart interaction with serial devices.

Automatically detects and interacts with common UART environments:
- Linux shells (busybox, bash, etc.)
- Login prompts
- Bootloaders (U-Boot, custom)
- Custom protocols

Usage:
    automation = UARTAutomation(backend)
    detected = await automation.detect_environment()

    if detected.is_shell:
        results = await automation.enumerate_shell()
"""

import asyncio
import re
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from ..backends import BusBackend, UARTConfig


class UARTPattern(Enum):
    """Types of UART environments we can detect."""
    UNKNOWN = auto()
    LOGIN_PROMPT = auto()
    SHELL = auto()
    BOOTLOADER = auto()
    CUSTOM_PROTOCOL = auto()
    BOOT_SEQUENCE = auto()
    ERROR_STATE = auto()


@dataclass
class DetectedEnvironment:
    """Results from environment detection."""
    pattern: UARTPattern
    confidence: float  # 0.0 to 1.0
    details: Dict[str, any] = field(default_factory=dict)
    captured_output: str = ""

    @property
    def is_shell(self) -> bool:
        return self.pattern == UARTPattern.SHELL

    @property
    def is_login(self) -> bool:
        return self.pattern == UARTPattern.LOGIN_PROMPT

    @property
    def is_bootloader(self) -> bool:
        return self.pattern == UARTPattern.BOOTLOADER


class UARTPatternLibrary:
    """
    Library of patterns for detecting common UART environments.
    """

    # Linux shell prompts
    SHELL_PROMPTS = [
        r'[\w\-]+[@:][\w\-]+[\$#]\s*$',  # user@host$ or root@host#
        r'[\w\-]+[\$#]\s*$',               # simple prompt: # or $
        r'/[\w/\-]*[\$#]\s*$',             # /path/to/dir$
        r'>\s*$',                          # Simple > prompt
    ]

    # Login prompts
    LOGIN_PROMPTS = [
        r'login:\s*$',
        r'username:\s*$',
        r'user:\s*$',
        r'password:\s*$',
        r'Password:\s*$',
    ]

    # Bootloader signatures
    BOOTLOADER_PATTERNS = [
        r'U-Boot\s+\d+\.\d+',              # U-Boot version
        r'Hit any key to stop autoboot',   # U-Boot autoboot
        r'=>\s*$',                         # U-Boot prompt
        r'Boot\s*Menu',                    # Generic boot menu
        r'Press\s+.*\s+to\s+interrupt',    # Interrupt boot sequence
        r'autoboot in \d+ seconds',        # Autoboot countdown
    ]

    # Common bootloader commands
    BOOTLOADER_COMMANDS = [
        'help', 'printenv', 'version', 'bdinfo'
    ]

    # Linux info gathering commands (safe, read-only)
    SHELL_ENUM_COMMANDS = [
        'uname -a',
        'cat /proc/cpuinfo',
        'cat /proc/version',
        'id',
        'pwd',
        'ls -la /',
        'cat /etc/issue',
        'cat /etc/passwd',
        'ps aux',
        'mount',
        'df -h',
        'ifconfig -a',
        'ip addr show',
    ]

    # Common default credentials
    COMMON_CREDENTIALS = [
        ('root', ''),
        ('root', 'root'),
        ('root', 'admin'),
        ('admin', 'admin'),
        ('admin', 'password'),
        ('user', 'user'),
        ('test', 'test'),
        ('admin', ''),
    ]

    @staticmethod
    def is_shell(text: str) -> bool:
        """Check if text looks like a shell prompt."""
        for pattern in UARTPatternLibrary.SHELL_PROMPTS:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False

    @staticmethod
    def is_login_prompt(text: str) -> bool:
        """Check if text looks like a login prompt."""
        text_lower = text.lower()
        for pattern in UARTPatternLibrary.LOGIN_PROMPTS:
            if re.search(pattern, text_lower, re.MULTILINE):
                return True
        return False

    @staticmethod
    def is_bootloader(text: str) -> bool:
        """Check if text looks like a bootloader."""
        for pattern in UARTPatternLibrary.BOOTLOADER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                return True
        return False


class UARTAutomation:
    """
    Smart UART automation based on detected environment.

    Automatically:
    - Detects what's on the other end (shell, login, bootloader, etc.)
    - Tries common credentials on login prompts
    - Runs safe enumeration commands on shells
    - Interacts with bootloaders
    - Logs all activity for analysis
    """

    def __init__(self, backend: BusBackend, log_callback: Optional[Callable] = None):
        """
        Initialize UART automation.

        Args:
            backend: BusBackend that supports UART
            log_callback: Optional function to call with log messages
        """
        self.backend = backend
        self.patterns = UARTPatternLibrary()
        self.log_callback = log_callback
        self._output_buffer = ""
        self._interaction_log: List[Dict] = []

    def log(self, message: str, level: str = "info"):
        """Log a message."""
        entry = {
            'timestamp': asyncio.get_event_loop().time(),
            'level': level,
            'message': message
        }
        self._interaction_log.append(entry)

        if self.log_callback:
            self.log_callback(message)

    async def configure(self, baudrate: int = 115200, **kwargs):
        """
        Configure UART parameters.

        Args:
            baudrate: Baud rate (default 115200)
            **kwargs: Additional UART config (data_bits, parity, stop_bits)
        """
        config = UARTConfig(baudrate=baudrate, **kwargs)
        self.backend.configure_uart(config)
        self.log(f"UART configured: {baudrate} baud")

    async def read(self, timeout_ms: int = 2000) -> str:
        """
        Read from UART with timeout.

        Args:
            timeout_ms: Read timeout in milliseconds

        Returns:
            String data read from UART
        """
        try:
            data = self.backend.uart_read(length=4096, timeout_ms=timeout_ms)
            text = data.decode(errors='ignore')
            self._output_buffer += text
            return text
        except Exception as e:
            self.log(f"Read error: {e}", level="error")
            return ""

    async def write(self, data: str):
        """
        Write to UART.

        Args:
            data: String to write (will be encoded to bytes)
        """
        try:
            self.backend.uart_write(data.encode())
            self.log(f"TX: {data.strip()}")
        except Exception as e:
            self.log(f"Write error: {e}", level="error")

    async def send_command(self, command: str, timeout_ms: int = 2000) -> str:
        """
        Send command and read response.

        Args:
            command: Command to send
            timeout_ms: Timeout for response

        Returns:
            Response text
        """
        await self.write(command + '\n')
        await asyncio.sleep(0.1)  # Brief delay for command processing
        response = await self.read(timeout_ms)
        return response

    async def detect_environment(self, initial_timeout: int = 5000) -> DetectedEnvironment:
        """
        Detect what type of UART environment we're connected to.

        Args:
            initial_timeout: How long to wait for initial output (ms)

        Returns:
            DetectedEnvironment with pattern and details
        """
        self.log("Detecting UART environment...")

        # Read initial output
        initial = await self.read(timeout_ms=initial_timeout)

        # Try sending enter to provoke a response
        await self.write('\n')
        await asyncio.sleep(0.2)
        after_enter = await self.read(timeout_ms=1000)

        combined = initial + after_enter

        # Check patterns in order of specificity
        if self.patterns.is_bootloader(combined):
            self.log("Detected: Bootloader")
            return DetectedEnvironment(
                pattern=UARTPattern.BOOTLOADER,
                confidence=0.9,
                captured_output=combined,
                details={'type': 'bootloader'}
            )

        if self.patterns.is_shell(combined):
            self.log("Detected: Shell prompt")
            return DetectedEnvironment(
                pattern=UARTPattern.SHELL,
                confidence=0.9,
                captured_output=combined,
                details={'type': 'shell'}
            )

        if self.patterns.is_login_prompt(combined):
            self.log("Detected: Login prompt")
            return DetectedEnvironment(
                pattern=UARTPattern.LOGIN_PROMPT,
                confidence=0.8,
                captured_output=combined,
                details={'type': 'login'}
            )

        # Check if it looks like boot sequence
        if any(word in combined.lower() for word in ['boot', 'loading', 'starting', 'init']):
            self.log("Detected: Boot sequence")
            return DetectedEnvironment(
                pattern=UARTPattern.BOOT_SEQUENCE,
                confidence=0.6,
                captured_output=combined,
                details={'type': 'boot'}
            )

        # Unknown
        self.log("Unknown UART environment")
        return DetectedEnvironment(
            pattern=UARTPattern.UNKNOWN,
            confidence=0.0,
            captured_output=combined,
            details={}
        )

    async def try_login(self, username: str, password: str, timeout_ms: int = 3000) -> bool:
        """
        Attempt login with given credentials.

        Args:
            username: Username to try
            password: Password to try
            timeout_ms: Timeout for login attempt

        Returns:
            True if login appears successful
        """
        self.log(f"Trying credentials: {username} / {'*' * len(password)}")

        # Send username
        await self.write(username + '\n')
        await asyncio.sleep(0.5)

        # Read response (should ask for password)
        response = await self.read(timeout_ms=1000)

        # Send password
        await self.write(password + '\n')
        await asyncio.sleep(0.5)

        # Read final response
        response = await self.read(timeout_ms=timeout_ms)

        # Check if we got a shell prompt
        if self.patterns.is_shell(response):
            self.log(f"✓ Login successful: {username}", level="success")
            return True

        # Check for login failure messages
        if any(word in response.lower() for word in ['incorrect', 'failed', 'denied', 'invalid']):
            self.log(f"✗ Login failed: {username}")
            return False

        self.log(f"? Login uncertain: {username}", level="warning")
        return False

    async def handle_login(self, try_bruteforce: bool = True) -> bool:
        """
        Handle login prompt - try common credentials.

        Args:
            try_bruteforce: Whether to try common credential list

        Returns:
            True if we successfully logged in
        """
        self.log("Attempting to bypass login...")

        if not try_bruteforce:
            return False

        # Try common credentials
        for username, password in self.patterns.COMMON_CREDENTIALS:
            if await self.try_login(username, password):
                return True

            # Brief delay between attempts
            await asyncio.sleep(0.5)

        self.log("All login attempts failed", level="warning")
        return False

    async def enumerate_shell(self) -> Dict[str, str]:
        """
        Run enumeration commands on a shell.

        Returns:
            Dict mapping command to output
        """
        self.log("Enumerating shell environment...")
        results = {}

        for cmd in self.patterns.SHELL_ENUM_COMMANDS:
            self.log(f"Running: {cmd}")

            response = await self.send_command(cmd, timeout_ms=3000)

            # Store result
            results[cmd] = response

            # Brief delay between commands
            await asyncio.sleep(0.3)

        self.log(f"Enumeration complete: {len(results)} commands executed")
        return results

    async def interact_bootloader(self) -> Dict[str, str]:
        """
        Interact with bootloader to gather information.

        Returns:
            Dict mapping command to output
        """
        self.log("Interacting with bootloader...")
        results = {}

        for cmd in self.patterns.BOOTLOADER_COMMANDS:
            self.log(f"Running: {cmd}")

            response = await self.send_command(cmd, timeout_ms=2000)

            results[cmd] = response

            await asyncio.sleep(0.2)

        self.log(f"Bootloader interaction complete: {len(results)} commands")
        return results

    async def auto_interact(self) -> Dict[str, any]:
        """
        Automatically detect environment and interact accordingly.

        Returns:
            Dict with detection results and interaction outcomes
        """
        # Detect environment
        detected = await self.detect_environment()

        result = {
            'detected': detected.pattern.name,
            'confidence': detected.confidence,
            'initial_output': detected.captured_output,
            'interaction_results': {}
        }

        # Handle based on pattern
        if detected.is_login:
            logged_in = await self.handle_login()
            result['login_success'] = logged_in

            if logged_in:
                # Re-detect (should now be shell)
                detected = await self.detect_environment(initial_timeout=1000)
                result['post_login_pattern'] = detected.pattern.name

                if detected.is_shell:
                    enum_results = await self.enumerate_shell()
                    result['enumeration'] = enum_results

        elif detected.is_shell:
            enum_results = await self.enumerate_shell()
            result['enumeration'] = enum_results

        elif detected.is_bootloader:
            boot_results = await self.interact_bootloader()
            result['bootloader_info'] = boot_results

        else:
            self.log("Unknown environment - no automatic actions taken")

        return result

    def get_interaction_log(self) -> List[Dict]:
        """Get all logged interactions."""
        return self._interaction_log.copy()

    def clear_buffer(self):
        """Clear the output buffer."""
        self._output_buffer = ""

    def get_buffer(self) -> str:
        """Get current output buffer."""
        return self._output_buffer
