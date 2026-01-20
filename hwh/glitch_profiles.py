"""
Glitch Profile Database

Knowledge base of chip-specific glitch attack parameters based on:
- Published research papers
- CTF writeups (ECSC, RHme, etc.)
- Community contributions
- Personal experimentation results

This allows starting attacks with known-good parameters rather than
blind sweeps, dramatically reducing time to successful exploitation.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum, auto
import json
from pathlib import Path


class AttackType(Enum):
    """Type of glitch attack."""
    VOLTAGE_GLITCH = auto()
    CLOCK_GLITCH = auto()
    EMFI = auto()
    LASER = auto()
    POWER_ANALYSIS = auto()


class TargetType(Enum):
    """What the attack targets."""
    RDP_BYPASS = "Read-out Protection Bypass"
    LOCKBIT_BYPASS = "Lockbit/Fuse Bypass"
    SECURE_BOOT = "Secure Boot Bypass"
    AUTH_BYPASS = "Authentication Bypass"
    PRIVILEGE_ESCALATION = "Privilege Escalation"
    CRYPTO_FAULT = "Cryptographic Fault Injection"
    INSTRUCTION_SKIP = "Instruction Skip"
    LOOP_ESCAPE = "Loop Escape"
    GENERAL = "General Fault Injection"


@dataclass
class GlitchParameters:
    """Successful glitch parameters."""
    width_ns: int           # Glitch pulse width in nanoseconds
    offset_ns: int          # Delay after trigger
    voltage_v: Optional[float] = None  # Voltage drop (for voltage glitching)
    repeat: int = 1         # Number of pulses
    notes: str = ""


@dataclass
class ParameterRange:
    """Range of parameters to search."""
    width_min: int
    width_max: int
    width_step: int
    offset_min: int
    offset_max: int
    offset_step: int
    voltage_min: Optional[float] = None
    voltage_max: Optional[float] = None
    voltage_step: Optional[float] = None


@dataclass
class GlitchProfile:
    """
    Complete glitch attack profile for a chip/attack combination.
    """
    # Identification
    name: str
    chip_family: str        # e.g., "STM32F1", "AVR", "ESP32"
    specific_chips: List[str] = field(default_factory=list)  # e.g., ["STM32F103C8", "STM32F103RB"]

    # Attack details
    attack_type: AttackType = AttackType.VOLTAGE_GLITCH
    target: TargetType = TargetType.GENERAL
    description: str = ""

    # Known successful parameters
    successful_params: List[GlitchParameters] = field(default_factory=list)

    # Recommended search range (if exact params unknown)
    recommended_range: Optional[ParameterRange] = None

    # Success indicators
    success_patterns: List[bytes] = field(default_factory=list)  # UART patterns indicating success
    success_description: str = ""

    # Timing/trigger info
    trigger_event: str = ""         # e.g., "Rising edge on UART TX", "200ms after reset"
    timing_notes: str = ""

    # Environmental factors
    voltage_nominal: float = 3.3    # Normal operating voltage
    clock_freq_mhz: Optional[float] = None
    temperature_notes: str = ""

    # Reliability
    success_rate: Optional[float] = None  # 0.0 to 1.0
    attempts_required: Optional[int] = None

    # Attribution
    source: str = ""                # Paper, CTF, researcher, etc.
    year: Optional[int] = None
    reference_url: str = ""

    # User notes
    notes: str = ""
    tags: List[str] = field(default_factory=list)


# =============================================================================
# PROFILE DATABASE
# =============================================================================

GLITCH_PROFILES: Dict[str, GlitchProfile] = {}


def register_profile(profile: GlitchProfile):
    """Register a glitch profile in the database."""
    GLITCH_PROFILES[profile.name] = profile


# =============================================================================
# STM32 PROFILES
# =============================================================================

register_profile(GlitchProfile(
    name="STM32F1_RDP_BYPASS",
    chip_family="STM32F1",
    specific_chips=["STM32F103C8", "STM32F103RB", "STM32F103CB", "STM32F103VB"],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.RDP_BYPASS,
    description="Bypass Read-out Protection (RDP) Level 1 on STM32F1 series during flash controller state transition",

    successful_params=[
        GlitchParameters(width_ns=120, offset_ns=3500, voltage_v=2.8, notes="ECSC23 Challenge 2 - Board A"),
        GlitchParameters(width_ns=85, offset_ns=3200, voltage_v=2.7, notes="Dev board with minimal decoupling"),
        GlitchParameters(width_ns=150, offset_ns=3480, voltage_v=2.9, notes="Production board with heavy decoupling"),
    ],

    recommended_range=ParameterRange(
        width_min=50, width_max=200, width_step=10,
        offset_min=1000, offset_max=5000, offset_step=100,
        voltage_min=2.5, voltage_max=3.0, voltage_step=0.1
    ),

    success_patterns=[
        b'>>>',           # OpenOCD successful connection
        b'target halted', # GDB connection
        b'Flash unlocked' # Custom bootloader message
    ],
    success_description="OpenOCD can connect via SWD and read flash contents",

    trigger_event="Rising edge during RDP check (typically 2-5ms after reset)",
    timing_notes="Glitch must occur during flash controller RDP verification",

    voltage_nominal=3.3,
    clock_freq_mhz=72.0,
    temperature_notes="More successful at room temperature (20-25°C)",

    success_rate=0.85,
    attempts_required=50,

    source="Multiple sources: ECSC23, Riscure blog, research papers",
    year=2023,
    reference_url="https://www.riscure.com/blog/",

    notes="Requires precise timing. Consider using Bus Pirate to monitor UART for boot messages.",
    tags=["stm32", "rdp", "voltage-glitch", "arm-cortex-m3", "well-documented"]
))

register_profile(GlitchProfile(
    name="STM32F4_RDP_BYPASS",
    chip_family="STM32F4",
    specific_chips=["STM32F407", "STM32F411", "STM32F429"],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.RDP_BYPASS,
    description="RDP Level 1 bypass on STM32F4 series - similar to F1 but requires stronger glitch",

    recommended_range=ParameterRange(
        width_min=80, width_max=250, width_step=15,
        offset_min=2000, offset_max=8000, offset_step=200,
        voltage_min=2.6, voltage_max=3.1, voltage_step=0.1
    ),

    success_patterns=[b'>>>'],
    success_description="SWD connection successful, flash readable",

    trigger_event="During RDP check, 3-8ms after reset",
    voltage_nominal=3.3,
    clock_freq_mhz=168.0,

    notes="Harder than F1 due to improved flash controller. May require EMFI instead.",
    tags=["stm32", "rdp", "voltage-glitch", "arm-cortex-m4"]
))

# =============================================================================
# AVR PROFILES
# =============================================================================

register_profile(GlitchProfile(
    name="ATMEGA328P_LOCKBIT_BYPASS",
    chip_family="AVR",
    specific_chips=["ATmega328P", "ATmega328", "ATmega168"],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.LOCKBIT_BYPASS,
    description="Bypass lockbit fuses on ATmega328P to dump protected flash",

    successful_params=[
        GlitchParameters(width_ns=200, offset_ns=1500, voltage_v=4.2, notes="Arduino Uno target"),
        GlitchParameters(width_ns=180, offset_ns=1450, voltage_v=4.3, notes="Standalone ATmega328P"),
    ],

    recommended_range=ParameterRange(
        width_min=100, width_max=300, width_step=20,
        offset_min=500, offset_max=2000, offset_step=50,
        voltage_min=4.0, voltage_max=4.8, voltage_step=0.1
    ),

    success_patterns=[
        b'Device signature',  # avrdude successful read
        b'reading flash'
    ],
    success_description="avrdude can read flash memory despite lockbits",

    trigger_event="During lockbit check in bootloader, ~1-2ms after reset",
    voltage_nominal=5.0,
    clock_freq_mhz=16.0,

    success_rate=0.75,
    attempts_required=100,

    source="Colin O'Flynn (ChipWhisperer), various CTFs",
    year=2019,
    reference_url="https://github.com/newaetech/chipwhisperer",

    notes="Well-documented attack. Works on most AVR chips with lockbits.",
    tags=["avr", "atmega", "lockbit", "voltage-glitch", "arduino"]
))

# =============================================================================
# ESP32 PROFILES
# =============================================================================

register_profile(GlitchProfile(
    name="ESP32_SECURE_BOOT_BYPASS",
    chip_family="ESP32",
    specific_chips=["ESP32-D0WDQ6", "ESP32-WROOM-32"],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.SECURE_BOOT,
    description="Bypass secure boot verification to load unsigned firmware",

    recommended_range=ParameterRange(
        width_min=80, width_max=150, width_step=10,
        offset_min=2000, offset_max=8000, offset_step=200,
        voltage_min=2.8, voltage_max=3.2, voltage_step=0.05
    ),

    success_patterns=[
        b'Boot mode: (1)',  # UART download mode
        b'ets'              # Boot ROM messages
    ],
    success_description="Device enters download mode, allows unsigned firmware upload",

    trigger_event="During secure boot signature check in BootROM",
    timing_notes="Glitch during signature verification, ~5-15ms after reset",

    voltage_nominal=3.3,
    clock_freq_mhz=240.0,

    source="LimitedResults, DEF CON 27",
    year=2019,
    reference_url="https://limitedresults.com/2019/08/esp32-glitching/",

    notes="Early ESP32 chips vulnerable. Newer revisions may be patched.",
    tags=["esp32", "secure-boot", "voltage-glitch", "wifi", "iot"]
))

# =============================================================================
# NXP/FREESCALE PROFILES
# =============================================================================

register_profile(GlitchProfile(
    name="KINETIS_K_FLASH_PROTECTION",
    chip_family="Kinetis K",
    specific_chips=["MK20DX256", "MK64FN1M0", "MK66FX1M0"],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.RDP_BYPASS,
    description="Bypass flash security on NXP Kinetis K-series (used in Teensy)",

    recommended_range=ParameterRange(
        width_min=50, width_max=200, width_step=15,
        offset_min=1000, offset_max=4000, offset_step=100
    ),

    success_patterns=[b'OpenSDA', b'target halted'],
    success_description="Debug interface accessible, flash readable",

    trigger_event="During flash security check",
    voltage_nominal=3.3,

    notes="Used in Teensy boards. Similar to STM32 attacks.",
    tags=["nxp", "kinetis", "arm-cortex-m4", "teensy"]
))

# =============================================================================
# PIC PROFILES
# =============================================================================

register_profile(GlitchProfile(
    name="PIC18F_CODE_PROTECTION",
    chip_family="PIC18F",
    specific_chips=["PIC18F4550", "PIC18F2550", "PIC18F4520"],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.LOCKBIT_BYPASS,
    description="Bypass code protection on PIC18F series",

    recommended_range=ParameterRange(
        width_min=150, width_max=400, width_step=25,
        offset_min=500, offset_max=2500, offset_step=100
    ),

    success_description="ICSP can read program memory despite code protection",

    trigger_event="During code protection check in bootloader",
    voltage_nominal=5.0,

    notes="PIC code protection known to be weak. Multiple bypass methods exist.",
    tags=["pic", "microchip", "code-protection"]
))

# =============================================================================
# GENERIC PROFILES (for unknown chips)
# =============================================================================

register_profile(GlitchProfile(
    name="GENERIC_ARM_CORTEX_M",
    chip_family="ARM Cortex-M",
    specific_chips=[],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.GENERAL,
    description="Generic voltage glitching profile for ARM Cortex-M chips (wide search)",

    recommended_range=ParameterRange(
        width_min=50, width_max=500, width_step=50,
        offset_min=1000, offset_max=10000, offset_step=500,
        voltage_min=2.5, voltage_max=3.2, voltage_step=0.1
    ),

    success_patterns=[
        b'>>>',
        b'# ',
        b'$ ',
        b'shell>',
        b'bootloader>',
        b'target halted'
    ],

    trigger_event="Varies - try reset, UART TX, clock edges",
    voltage_nominal=3.3,

    notes="Wide search parameters for unknown ARM Cortex-M targets. Refine after finding successes.",
    tags=["generic", "arm-cortex-m", "wide-search"]
))

register_profile(GlitchProfile(
    name="GENERIC_AVR",
    chip_family="AVR",
    specific_chips=[],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.GENERAL,
    description="Generic voltage glitching profile for AVR chips",

    recommended_range=ParameterRange(
        width_min=100, width_max=400, width_step=30,
        offset_min=500, offset_max=3000, offset_step=100,
        voltage_min=4.0, voltage_max=5.2, voltage_step=0.1
    ),

    trigger_event="Reset or clock edge",
    voltage_nominal=5.0,

    notes="Generic AVR profile. Most AVR chips have similar glitch characteristics.",
    tags=["generic", "avr", "wide-search"]
))


# =============================================================================
# PROFILE QUERY FUNCTIONS
# =============================================================================

def get_profile(name: str) -> Optional[GlitchProfile]:
    """Get a profile by name."""
    return GLITCH_PROFILES.get(name)


def find_profiles_for_chip(chip: str) -> List[GlitchProfile]:
    """
    Find all profiles applicable to a specific chip.

    Args:
        chip: Chip name (e.g., "STM32F103C8", "ATmega328P")

    Returns:
        List of matching profiles, sorted by specificity
    """
    matches = []

    chip_upper = chip.upper()

    for profile in GLITCH_PROFILES.values():
        # Exact match in specific_chips list
        if any(c.upper() == chip_upper for c in profile.specific_chips):
            matches.append((profile, 2))  # High priority
            continue

        # Partial match (e.g., "STM32F103" matches "STM32F103C8")
        if any(chip_upper.startswith(c.upper()) for c in profile.specific_chips):
            matches.append((profile, 1))  # Medium priority
            continue

        # Family match (e.g., "STM32F1" matches "STM32F103C8")
        if chip_upper.startswith(profile.chip_family.upper().replace(" ", "")):
            matches.append((profile, 0))  # Low priority

    # Sort by priority (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)

    return [profile for profile, _ in matches]


def find_profiles_by_attack(attack_type: AttackType, target: Optional[TargetType] = None) -> List[GlitchProfile]:
    """Find profiles by attack type and optionally target."""
    matches = []

    for profile in GLITCH_PROFILES.values():
        if profile.attack_type == attack_type:
            if target is None or profile.target == target:
                matches.append(profile)

    return matches


def search_profiles(query: str) -> List[GlitchProfile]:
    """
    Search profiles by keyword.

    Searches name, chip_family, specific_chips, description, and tags.
    """
    matches = []
    query_lower = query.lower()

    for profile in GLITCH_PROFILES.values():
        # Search various fields
        searchable = [
            profile.name.lower(),
            profile.chip_family.lower(),
            profile.description.lower(),
            ' '.join(profile.specific_chips).lower(),
            ' '.join(profile.tags).lower()
        ]

        if any(query_lower in field for field in searchable):
            matches.append(profile)

    return matches


def list_all_profiles() -> List[GlitchProfile]:
    """Get all profiles."""
    return list(GLITCH_PROFILES.values())


def get_profile_summary() -> Dict[str, int]:
    """Get summary statistics of the profile database."""
    return {
        'total_profiles': len(GLITCH_PROFILES),
        'by_attack_type': {
            attack.name: len([p for p in GLITCH_PROFILES.values() if p.attack_type == attack])
            for attack in AttackType
        },
        'by_target': {
            target.value: len([p for p in GLITCH_PROFILES.values() if p.target == target])
            for target in TargetType
        }
    }


# =============================================================================
# PROFILE I/O (for custom profiles)
# =============================================================================

def export_profile_to_json(profile: GlitchProfile) -> str:
    """Export a profile to JSON string."""
    data = {
        'name': profile.name,
        'chip_family': profile.chip_family,
        'specific_chips': profile.specific_chips,
        'attack_type': profile.attack_type.name,
        'target': profile.target.name,
        'description': profile.description,
        'successful_params': [
            {
                'width_ns': p.width_ns,
                'offset_ns': p.offset_ns,
                'voltage_v': p.voltage_v,
                'repeat': p.repeat,
                'notes': p.notes
            }
            for p in profile.successful_params
        ],
        'recommended_range': {
            'width_min': profile.recommended_range.width_min,
            'width_max': profile.recommended_range.width_max,
            'width_step': profile.recommended_range.width_step,
            'offset_min': profile.recommended_range.offset_min,
            'offset_max': profile.recommended_range.offset_max,
            'offset_step': profile.recommended_range.offset_step,
        } if profile.recommended_range else None,
        'success_patterns': [p.decode('latin1') for p in profile.success_patterns],
        'trigger_event': profile.trigger_event,
        'voltage_nominal': profile.voltage_nominal,
        'source': profile.source,
        'notes': profile.notes,
        'tags': profile.tags
    }

    return json.dumps(data, indent=2)


def save_custom_profile(profile: GlitchProfile, filepath: Path):
    """Save a custom profile to JSON file."""
    with open(filepath, 'w') as f:
        f.write(export_profile_to_json(profile))


def load_custom_profile(filepath: Path) -> Optional[GlitchProfile]:
    """Load a custom profile from JSON file."""
    # TODO: Implement JSON -> GlitchProfile parsing
    pass


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    # Example: Find profiles for a specific chip
    print("=== Profiles for STM32F103C8 ===")
    profiles = find_profiles_for_chip("STM32F103C8")
    for p in profiles:
        print(f"\n{p.name}")
        print(f"  Description: {p.description}")
        if p.successful_params:
            print(f"  Known params: width={p.successful_params[0].width_ns}ns, offset={p.successful_params[0].offset_ns}ns")
        if p.recommended_range:
            r = p.recommended_range
            print(f"  Search range: width {r.width_min}-{r.width_max}ns, offset {r.offset_min}-{r.offset_max}ns")

    print("\n\n=== All RDP Bypass Profiles ===")
    rdp_profiles = find_profiles_by_attack(AttackType.VOLTAGE_GLITCH, TargetType.RDP_BYPASS)
    for p in rdp_profiles:
        print(f"  - {p.name} ({p.chip_family})")

    print("\n\n=== Database Summary ===")
    summary = get_profile_summary()
    print(f"Total profiles: {summary['total_profiles']}")
    print(f"By attack type: {summary['by_attack_type']}")
