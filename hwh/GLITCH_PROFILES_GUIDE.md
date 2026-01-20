# Glitch Profile Database - Usage Guide

The glitch profile database provides **chip-specific attack parameters** to dramatically reduce time from "hours of blind searching" to "minutes with targeted parameters."

## Quick Start

### 1. Find Profiles for Your Target

```python
from hwh.glitch_profiles import find_profiles_for_chip

# Find all profiles for your chip
profiles = find_profiles_for_chip("STM32F103C8")

for profile in profiles:
    print(f"{profile.name}: {profile.description}")
    if profile.successful_params:
        p = profile.successful_params[0]
        print(f"  Known success: width={p.width_ns}ns, offset={p.offset_ns}ns")
```

### 2. Use Adaptive Workflow (Recommended)

The **adaptive workflow** automatically uses profiles:

```python
from hwh.workflows import create_adaptive_glitch_workflow
from hwh.glitch_profiles import TargetType
from hwh.tui.device_pool import DevicePool

# Setup device pool
pool = DevicePool()
await pool.scan_devices()

# Create adaptive workflow - it will auto-select the best profile
workflow = create_adaptive_glitch_workflow(
    target_chip="STM32F103C8",
    attack_target=TargetType.RDP_BYPASS,
    success_patterns=[b'>>>', b'target halted']
)

# Run it - workflow adapts based on results
result = await workflow.run(pool)

print(f"Success rate: {result.results['success_rate'] * 100:.2f}%")
print(f"Profile used: {result.results['profile_used']}")
print(f"Phases: {result.results['phase_results']}")
```

### 3. Manual Profile Usage

Or use profiles manually:

```python
from hwh.glitch_profiles import get_profile
from hwh.workflows import GlitchMonitorWorkflow, GlitchParameters, SuccessCriteria

# Get specific profile
profile = get_profile("STM32F1_RDP_BYPASS")

# Use its recommended range
r = profile.recommended_range
params = GlitchParameters(
    width_min=r.width_min,
    width_max=r.width_max,
    width_step=r.width_step,
    offset_min=r.offset_min,
    offset_max=r.offset_max,
    offset_step=r.offset_step,
    attempts_per_setting=5
)

# Use its success patterns
criteria = SuccessCriteria(
    patterns=profile.success_patterns,
    timeout_ms=1000
)

# Create workflow
workflow = GlitchMonitorWorkflow(params, criteria)
```

## Available Profiles

### STM32 Family

**STM32F1_RDP_BYPASS** - STM32F103C8/RB/CB/VB
- **Target:** Read-out Protection Level 1 bypass
- **Known params:** width 85-150ns, offset 3200-3500ns
- **Success rate:** ~85%
- **Source:** ECSC23, Riscure, research papers

**STM32F4_RDP_BYPASS** - STM32F407/F411/F429
- **Target:** RDP Level 1 bypass (harder than F1)
- **Recommended range:** width 80-250ns, offset 2000-8000ns
- **Note:** May require EMFI instead of voltage glitching

### AVR Family

**ATMEGA328P_LOCKBIT_BYPASS** - ATmega328P (Arduino)
- **Target:** Lockbit fuse bypass to dump protected flash
- **Known params:** width 180-200ns, offset 1450-1500ns @ 5V
- **Success rate:** ~75%
- **Source:** ChipWhisperer, CTFs

### ESP32 Family

**ESP32_SECURE_BOOT_BYPASS** - ESP32-D0WDQ6, ESP32-WROOM-32
- **Target:** Secure boot verification bypass
- **Recommended range:** width 80-150ns, offset 2000-8000ns
- **Note:** Early revisions vulnerable, newer chips may be patched
- **Source:** LimitedResults, DEF CON 27

### Generic Profiles

**GENERIC_ARM_CORTEX_M** - Unknown ARM Cortex-M chips
- **Wide search:** width 50-500ns (step 50), offset 1000-10000ns (step 500)
- **Use when:** No specific profile available

**GENERIC_AVR** - Unknown AVR chips
- **Wide search:** width 100-400ns (step 30), offset 500-3000ns (step 100)
- **Voltage:** 4.0-5.2V

## Workflow Execution Phases

The adaptive workflow executes in phases:

### Phase 1: Known Parameters (if available)
- Tries documented successful parameters first
- 50 attempts per known parameter set
- **Time saved:** Minutes instead of hours

### Phase 2: Coarse Sweep (if Phase 1 fails)
- Uses profile's recommended_range (if available)
- Falls back to generic wide search
- 3 attempts per parameter combination
- **Purpose:** Find success regions

### Phase 3: Fine Tuning (if successes found)
- Refines ±50ns around each success point
- Step size: 5ns
- 10 attempts per combination
- **Purpose:** Map exact success boundaries

## Example: STM32F103 RDP Bypass

Complete example attacking STM32F103C8:

```python
import asyncio
from hwh.tui.device_pool import DevicePool
from hwh.workflows import create_adaptive_glitch_workflow
from hwh.glitch_profiles import TargetType

async def attack_stm32_rdp():
    # Setup
    pool = DevicePool()
    await pool.scan_devices()

    # Create adaptive workflow
    workflow = create_adaptive_glitch_workflow(
        target_chip="STM32F103C8",
        attack_target=TargetType.RDP_BYPASS,
        success_patterns=[b'>>>', b'target halted'],

        # Optional: customize behavior
        try_known_params_first=True,
        known_params_attempts=50,
        coarse_sweep_enabled=True,
        fine_tune_enabled=True
    )

    # Run attack
    print("Starting adaptive glitch attack on STM32F103C8...")
    result = await workflow.run(pool)

    # Results
    print(f"\n=== Attack Complete ===")
    print(f"Duration: {result.duration_seconds:.1f} seconds")
    print(f"Total iterations: {result.results['total_iterations']}")
    print(f"Successes: {result.results['success_count']}")
    print(f"Success rate: {result.results['success_rate'] * 100:.2f}%")

    # Phase breakdown
    print(f"\nPhase Results:")
    for phase, data in result.results['phase_results'].items():
        print(f"  {phase}: {data['attempts']} attempts, {data['successes']} successes")

    # Success map
    print(f"\nSuccess Map:")
    for width, offsets in result.results['success_map'].items():
        print(f"  Width {width}ns: offsets {offsets}")

    # Save successful parameters for future use
    if result.results['successes']:
        best = result.results['successes'][0]
        print(f"\nBest parameters:")
        print(f"  Width: {best['parameters']['width_ns']}ns")
        print(f"  Offset: {best['parameters']['offset_ns']}ns")

asyncio.run(attack_stm32_rdp())
```

## Adding Custom Profiles

Found new parameters? Add them to the database:

```python
from hwh.glitch_profiles import GlitchProfile, GlitchParameters, ParameterRange
from hwh.glitch_profiles import AttackType, TargetType, register_profile

# Create profile
custom_profile = GlitchProfile(
    name="MY_DEVICE_CUSTOM_ATTACK",
    chip_family="MyChip",
    specific_chips=["MyChip123", "MyChip456"],
    attack_type=AttackType.VOLTAGE_GLITCH,
    target=TargetType.RDP_BYPASS,
    description="Custom attack on my device",

    successful_params=[
        GlitchParameters(
            width_ns=125,
            offset_ns=3500,
            voltage_v=2.9,
            notes="Found in lab testing 2026-01-20"
        )
    ],

    recommended_range=ParameterRange(
        width_min=100, width_max=150, width_step=5,
        offset_min=3000, offset_max=4000, offset_step=50
    ),

    success_patterns=[b'shell>', b'# '],
    trigger_event="After reset, during boot",
    voltage_nominal=3.3,

    source="Personal research",
    notes="Works reliably at room temperature"
)

# Register it
register_profile(custom_profile)

# Now it's available
from hwh.glitch_profiles import find_profiles_for_chip
profiles = find_profiles_for_chip("MyChip123")
```

## Search and Query

### Search by Keyword

```python
from hwh.glitch_profiles import search_profiles

# Search by keyword
results = search_profiles("stm32")
results = search_profiles("rdp")
results = search_profiles("voltage-glitch")
```

### Find by Attack Type

```python
from hwh.glitch_profiles import find_profiles_by_attack, AttackType, TargetType

# All voltage glitch attacks
voltage_profiles = find_profiles_by_attack(AttackType.VOLTAGE_GLITCH)

# Specifically RDP bypass attacks
rdp_profiles = find_profiles_by_attack(
    AttackType.VOLTAGE_GLITCH,
    TargetType.RDP_BYPASS
)
```

### Database Statistics

```python
from hwh.glitch_profiles import get_profile_summary

stats = get_profile_summary()
print(f"Total profiles: {stats['total_profiles']}")
print(f"By attack type: {stats['by_attack_type']}")
print(f"By target: {stats['by_target']}")
```

## Profile Quality Indicators

When evaluating profiles:

### High Confidence
- **Multiple successful_params** documented
- **success_rate** > 0.7
- **Source** from published research or CTFs
- **Specific chip models** listed

Example: `STM32F1_RDP_BYPASS` - 3 documented success params, 85% rate

### Medium Confidence
- **Recommended range** provided
- **Source** from community contributions
- **Chip family** match but not specific models

Example: `STM32F4_RDP_BYPASS` - recommended range, no exact params yet

### Low Confidence (Generic)
- **Wide search range**
- **No specific parameters**
- **Generic family match**

Example: `GENERIC_ARM_CORTEX_M` - starting point for unknown chips

## Time Savings

**Without profiles** (blind search):
```
Width: 50-500ns (step 50) = 10 values
Offset: 1000-10000ns (step 500) = 19 values
Attempts: 3 per combination
Total: 10 × 19 × 3 = 570 attempts
Time: ~30-60 minutes (with resets)
```

**With profile** (targeted search):
```
Phase 1: Try 3 known params × 50 attempts = 150 attempts
  SUCCESS after ~5 minutes! ✓

Phase 3 (optional): Fine-tune ±50ns
  Map exact boundaries

Time saved: 25-55 minutes per attack
```

## Contributing

Found new parameters? Please contribute back to the database:

1. Document successful parameters (width, offset, voltage)
2. Test reliability (success rate over multiple attempts)
3. Note environmental factors (board design, decoupling, temperature)
4. Create profile and submit PR or issue

## References

- **ChipWhisperer Documentation** - https://chipwhisperer.readthedocs.io/
- **Riscure Blog** - https://www.riscure.com/blog/
- **ECSC CTF Challenges** - Hardware security competitions
- **RHme (Riscure Hack Me)** - https://github.com/Riscure/Rhme-2016
- **LimitedResults ESP32** - https://limitedresults.com/2019/08/esp32-glitching/

---

*Profile database is community-driven. Contributions welcome!*
