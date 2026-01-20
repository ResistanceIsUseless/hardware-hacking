"""
Configuration system for glitching campaigns

Enables zero-code target changes via config files.

Based on patterns from glitch-o-bolt by 0xRoM
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional, Dict, Any
from pathlib import Path
import importlib.util


@dataclass
class GlitchParams:
    """Glitch timing parameters"""
    width_ns: float = 0.0      # Glitch width in nanoseconds
    offset_ns: float = 0.0     # Delay after trigger in nanoseconds
    repeat: int = 1            # Number of times to repeat

    def to_bolt_cycles(self) -> Tuple[int, int]:
        """Convert to Curious Bolt cycles (8.3ns resolution)"""
        repeat_cycles = max(1, int(self.width_ns / 8.3))
        offset_cycles = int(self.offset_ns / 8.3)
        return (repeat_cycles, offset_cycles)


@dataclass
class SerialConfig:
    """Serial port configuration"""
    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    data_bits: int = 8
    parity: str = "N"
    stop_bits: int = 1
    timeout: float = 1.0


@dataclass
class TriggerConfig:
    """GPIO trigger configuration"""
    pin: int
    mode: str  # "pull-up", "pull-down", "disabled"
    enabled: bool = False

    @classmethod
    def from_symbol(cls, pin: int, symbol: str, enabled: bool):
        """
        Create from glitch-o-bolt style symbol

        Args:
            pin: GPIO pin number (0-7)
            symbol: "^" (pull-up), "v" (pull-down), "-" (disabled)
            enabled: Whether trigger is enabled
        """
        mode_map = {
            "^": "pull-up",
            "v": "pull-down",
            "-": "disabled"
        }
        return cls(pin=pin, mode=mode_map.get(symbol, "disabled"), enabled=enabled)

    def to_symbol(self) -> str:
        """Convert to glitch-o-bolt style symbol"""
        symbol_map = {
            "pull-up": "^",
            "pull-down": "v",
            "disabled": "-"
        }
        return symbol_map.get(self.mode, "-")


@dataclass
class GlitchConfig:
    """Complete glitching campaign configuration"""
    name: str = "default"
    serial: SerialConfig = field(default_factory=SerialConfig)
    glitch: GlitchParams = field(default_factory=GlitchParams)
    triggers: List[TriggerConfig] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    custom_functions: Dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure we have 8 triggers (for Curious Bolt)"""
        if not self.triggers:
            self.triggers = [
                TriggerConfig(pin=i, mode="disabled", enabled=False)
                for i in range(8)
            ]


def load_config_file(config_path: str | Path) -> GlitchConfig:
    """
    Load configuration from Python file

    Compatible with glitch-o-bolt config format.

    Example config file:
        ```python
        SERIAL_PORT = '/dev/ttyUSB0'
        BAUD_RATE = 115200

        LENGTH = 0
        REPEAT = 42  # Width in 8.3ns cycles
        DELAY = 0    # Offset in 8.3ns cycles

        triggers = [
            ['^', True],   # Pin 0: pull-up enabled
            ['-', False],  # Pin 1: disabled
            ['v', True],   # Pin 2: pull-down enabled
            # ... up to 8 pins
        ]

        conditions = [
            ["Flag", True, "ctf", "stop_glitching"],
        ]

        def stop_glitching():
            print("Flag found!")
        ```

    Returns:
        GlitchConfig object
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load the Python module
    spec = importlib.util.spec_from_file_location("campaign_config", config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load config file: {config_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Extract configuration
    config = GlitchConfig(name=config_path.stem)

    # Serial configuration
    config.serial.port = getattr(module, 'SERIAL_PORT', '/dev/ttyUSB0')
    config.serial.baudrate = getattr(module, 'BAUD_RATE', 115200)

    # Glitch parameters (convert from Bolt cycles to nanoseconds)
    repeat_cycles = getattr(module, 'REPEAT', 0)
    delay_cycles = getattr(module, 'DELAY', 0)

    config.glitch.width_ns = repeat_cycles * 8.3
    config.glitch.offset_ns = delay_cycles * 8.3

    # Triggers
    if hasattr(module, 'triggers'):
        config.triggers = []
        for i, (symbol, enabled) in enumerate(module.triggers):
            trigger = TriggerConfig.from_symbol(i, symbol, enabled)
            config.triggers.append(trigger)

    # Conditions
    if hasattr(module, 'conditions'):
        config.conditions = []
        for cond in module.conditions:
            if len(cond) >= 4:
                name, enabled, pattern, func_name = cond[:4]
                config.conditions.append({
                    'name': name,
                    'enabled': enabled,
                    'pattern': pattern,
                    'function': func_name
                })

    # Custom functions
    if hasattr(module, 'conditions'):
        for cond in module.conditions:
            if len(cond) >= 4:
                func_name = cond[3]
                if func_name and hasattr(module, func_name):
                    config.custom_functions[func_name] = getattr(module, func_name)

    return config


def save_config_file(config: GlitchConfig, output_path: str | Path) -> None:
    """
    Save configuration to Python file

    Generates glitch-o-bolt compatible config format.
    """
    output_path = Path(output_path)

    # Convert glitch params to Bolt cycles
    repeat_cycles, delay_cycles = config.glitch.to_bolt_cycles()

    # Generate trigger list
    trigger_lines = []
    for trigger in config.triggers:
        symbol = trigger.to_symbol()
        trigger_lines.append(f"    ['{symbol}', {trigger.enabled}],  # Pin {trigger.pin}")

    # Generate conditions list
    condition_lines = []
    for cond in config.conditions:
        name = cond['name']
        enabled = cond['enabled']
        pattern = cond['pattern']
        func = cond['function']
        condition_lines.append(f'    ["{name}", {enabled}, "{pattern}", "{func}"],')

    # Write config file
    content = f'''"""
Generated glitch configuration: {config.name}
"""

# Serial port settings
SERIAL_PORT = '{config.serial.port}'
BAUD_RATE = {config.serial.baudrate}

# Glitch parameters (in 8.3ns cycles)
LENGTH = 0  # Placeholder
REPEAT = {repeat_cycles}  # ~{config.glitch.width_ns:.1f}ns glitch width
DELAY = {delay_cycles}    # ~{config.glitch.offset_ns:.1f}ns delay after trigger

# GPIO triggers
# ^ = pull-up, v = pull-down, - = disabled
triggers = [
{chr(10).join(trigger_lines)}
]

# Automation conditions
# Format: [name, enabled, pattern, function_name]
conditions = [
{chr(10).join(condition_lines)}
]

# Custom automation functions
# Define your condition action functions here
# Example:
# def stop_glitching():
#     print("Success detected!")
'''

    output_path.write_text(content)


# Example template configurations

def create_bolt_ctf_challenge2_config() -> GlitchConfig:
    """Generate config for Bolt CTF Challenge 2"""
    config = GlitchConfig(name="bolt_ctf_challenge2")

    config.serial.port = "/dev/cu.usbserial-110"
    config.serial.baudrate = 115200

    config.glitch.width_ns = 42 * 8.3  # ~350ns
    config.glitch.offset_ns = 0

    config.triggers = [
        TriggerConfig(pin=0, mode="pull-up", enabled=True),
    ] + [
        TriggerConfig(pin=i, mode="disabled", enabled=False)
        for i in range(1, 8)
    ]

    config.conditions = [
        {
            'name': 'Flag',
            'enabled': True,
            'pattern': 'ctf',
            'function': 'stop_glitching'
        },
        {
            'name': 'Start',
            'enabled': True,
            'pattern': 'Hold one of',
            'function': 'start_challenge'
        }
    ]

    return config


def create_parameter_sweep_config() -> GlitchConfig:
    """Generate config for automated parameter sweeping"""
    config = GlitchConfig(name="parameter_sweep")

    config.serial.port = "/dev/ttyUSB0"
    config.serial.baudrate = 115200

    config.glitch.width_ns = 10 * 8.3  # Start small
    config.glitch.offset_ns = 0

    config.conditions = [
        {
            'name': 'Success',
            'enabled': True,
            'pattern': r'(success|flag|ctf)',
            'function': 'handle_success'
        },
        {
            'name': 'Crash',
            'enabled': True,
            'pattern': r'(reset|crash|fault)',
            'function': 'handle_crash'
        }
    ]

    return config
