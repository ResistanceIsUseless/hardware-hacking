#!/usr/bin/env python3
"""
Example 3: STM32 RDP Bypass with Adaptive Workflow

This example demonstrates:
- Multi-device coordination (glitcher + monitor)
- Role assignment and device pool management
- Adaptive glitch workflow with profile database
- Three-phase attack (known params → coarse → fine)
- Success mapping and result analysis

Usage:
    python3 examples/03_stm32_rdp_bypass.py

Requirements:
    - Curious Bolt (glitcher) connected
    - Bus Pirate or similar (UART monitor) connected
    - Bolt wired to target STM32 device
    - Target powered and ready

Wiring:
    Bolt → Target:
        VCC → VCC (power injection point)
        TRIGGER → RESET or other trigger
        GND → GND

    Monitor → Target:
        RX → TX (target's UART TX)
        GND → GND

WARNING: This is an educational example. Only test on devices you own.
         Bypassing security protections on devices you don't own is illegal.
"""
import asyncio
from hwh.tui.device_pool import DevicePool, DeviceRole
from hwh.workflows import create_adaptive_glitch_workflow
from hwh.glitch_profiles import TargetType, find_profiles_for_chip


async def main():
    print("="*70)
    print("  STM32 RDP Bypass Example - Adaptive Glitch Workflow")
    print("="*70)
    print()
    print("⚠️  WARNING: For educational and authorized testing only!")
    print("   Only test on devices you own.")
    print()
    print("="*70)

    # Setup device pool
    pool = DevicePool()
    print("\nScanning for devices...")
    devices = await pool.scan_devices()

    if len(devices) < 2:
        print(f"\n❌ Need at least 2 devices (found {len(devices)})")
        print("\nRequired:")
        print("  - Glitcher (Curious Bolt)")
        print("  - UART Monitor (Bus Pirate, Tigard, etc.)")
        return

    print(f"✓ Found {len(devices)} device(s)\n")

    # Show available profiles
    print("="*70)
    print("Available STM32 profiles:")
    print("="*70)
    profiles = find_profiles_for_chip("STM32F103")
    if profiles:
        for p in profiles:
            print(f"\n{p.name}:")
            print(f"  Target: {p.target.value}")
            print(f"  Success rate: {p.success_rate * 100 if p.success_rate else 'Unknown'}%")
            if p.successful_params:
                print(f"  Known params: {len(p.successful_params)} documented")
    print()

    # Get recommendations
    print("="*70)
    print("Getting device recommendations...")
    print("="*70)
    recommendations = pool.recommend_for_task("glitch STM32 with UART monitoring")

    if recommendations:
        print("\nRecommended devices:")
        for rec in recommendations:
            print(f"  {rec.device_id} ({rec.confidence:.0%} confidence)")
            print(f"    Role: {rec.suggested_role.name}")
            print(f"    Reason: {rec.reason}")
        print()

    # Setup devices
    glitchers = pool.get_devices_by_capability("voltage_glitch")
    monitors = pool.get_devices_by_capability("uart")

    if not glitchers:
        print("❌ No glitcher found. Is Curious Bolt connected?")
        return

    if not monitors:
        print("❌ No UART monitor found. Is Bus Pirate connected?")
        return

    glitcher_id = glitchers[0]
    monitor_id = monitors[0]

    # Assign roles
    pool.assign_role(glitcher_id, DeviceRole.GLITCHER)
    pool.assign_role(monitor_id, DeviceRole.MONITOR)

    print(f"✓ Assigned {glitcher_id} as GLITCHER")
    print(f"✓ Assigned {monitor_id} as MONITOR")

    # Connect
    print("\nConnecting to devices...")
    if not await pool.connect(glitcher_id):
        print(f"❌ Failed to connect to {glitcher_id}")
        return
    print(f"  ✓ Connected to glitcher")

    if not await pool.connect(monitor_id):
        print(f"❌ Failed to connect to {monitor_id}")
        return
    print(f"  ✓ Connected to monitor")

    # Display pool status
    print("\n" + "="*70)
    print("Device Pool Status:")
    print("="*70)
    pool.display_status()

    # Create adaptive workflow
    print("="*70)
    print("Creating adaptive glitch workflow...")
    print("="*70)

    workflow = create_adaptive_glitch_workflow(
        target_chip="STM32F103C8",
        attack_target=TargetType.RDP_BYPASS,
        success_patterns=[
            b'>>>',           # OpenOCD prompt
            b'target halted', # GDB connection
            b'Debug access'   # Success indicator
        ],
        try_known_params_first=True,
        known_params_attempts=50,
        coarse_sweep_enabled=True,
        fine_tune_enabled=True
    )

    print("\n✓ Workflow configured:")
    print("  Phase 1: Try known STM32F1 parameters (50 attempts each)")
    print("  Phase 2: Coarse sweep if Phase 1 fails")
    print("  Phase 3: Fine-tune around successes")
    print("\nEstimated time:")
    print("  Best case: ~5 minutes (known params work)")
    print("  Worst case: ~30 minutes (full sweep)")

    # Run the workflow
    print("\n" + "="*70)
    print("Starting adaptive glitch attack...")
    print("="*70)
    print("\n(Press Ctrl+C to cancel)\n")

    try:
        result = await workflow.run(pool)

        # Display results
        print("\n" + "="*70)
        print("=== Attack Complete ===")
        print("="*70)
        print(f"\nStatus: {result.status.name}")
        print(f"Duration: {result.duration_seconds:.1f} seconds ({result.duration_seconds/60:.1f} minutes)")

        print(f"\n--- Statistics ---")
        print(f"Total iterations: {result.results['total_iterations']}")
        print(f"Successes: {result.results['success_count']}")
        print(f"Success rate: {result.results['success_rate'] * 100:.2f}%")

        # Phase breakdown
        if result.results['phase_results']:
            print(f"\n--- Phase Results ---")
            for phase, data in result.results['phase_results'].items():
                print(f"{phase}:")
                print(f"  Attempts: {data['attempts']}")
                print(f"  Successes: {data['successes']}")

        # Success map
        if result.results['success_map']:
            print(f"\n--- Success Map ---")
            print("Parameters that worked:")
            for width, offsets in sorted(result.results['success_map'].items()):
                print(f"  Width {width}ns: offsets {sorted(offsets)}")

        # Best parameters
        if result.results['successes']:
            print(f"\n--- Best Parameters ---")
            best = result.results['successes'][0]
            print(f"Width: {best['parameters']['width_ns']}ns")
            print(f"Offset: {best['parameters']['offset_ns']}ns")
            print(f"\nOutput captured:")
            output = best['details']['output'][:300]
            print(f"  {output}")

            print(f"\n💾 Save these parameters for future attacks!")

        else:
            print("\n❌ No successes found")
            print("\nTroubleshooting:")
            print("  - Check wiring (VCC injection, trigger, GND)")
            print("  - Verify target is powered and responding")
            print("  - Try different trigger timing")
            print("  - Check UART monitor is capturing output")

    except KeyboardInterrupt:
        print("\n\n⚠️  Attack cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error during attack: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    print("\n" + "="*70)
    print("Cleaning up...")
    await pool.disconnect_all()
    print("✓ Done")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
