"""
Adaptive Glitch Workflow

Intelligently selects glitch parameters based on:
1. Known profiles for target chip (if available)
2. Coarse sweep to find success regions
3. Fine refinement around successful parameters
4. Building a device-specific success map

This dramatically reduces time to successful glitch from hours to minutes
when attacking known chip families.
"""

import asyncio
from typing import Optional, List, Dict
from dataclasses import dataclass

from .base import ParameterSweepWorkflow, MonitoringMixin, WorkflowResult, WorkflowStatus
from .glitch_monitor import GlitchParameters, SuccessCriteria
from ..glitch_profiles import (
    GlitchProfile, find_profiles_for_chip, get_profile,
    AttackType, TargetType
)
from ..tui.device_pool import DeviceRole
from ..backends import GlitchBackend, BusBackend, GlitchConfig


@dataclass
class AdaptiveGlitchConfig:
    """Configuration for adaptive glitch workflow."""
    target_chip: Optional[str] = None      # e.g., "STM32F103C8"
    profile_name: Optional[str] = None     # Or specify profile directly
    attack_target: Optional[TargetType] = None  # e.g., RDP_BYPASS

    # Adaptive behavior
    try_known_params_first: bool = True    # Try documented successful params
    known_params_attempts: int = 50        # Attempts per known parameter

    coarse_sweep_enabled: bool = True      # Do coarse sweep if known params fail
    coarse_attempts_per_setting: int = 3   # Attempts during coarse sweep

    fine_tune_enabled: bool = True         # Refine around successes
    fine_tune_range_ns: int = 50           # ±range around success for fine tuning
    fine_tune_step_ns: int = 5             # Step size for fine tuning
    fine_tune_attempts: int = 10           # Attempts during fine tuning

    # Success criteria
    success_patterns: List[bytes] = None
    timeout_ms: int = 1000


class AdaptiveGlitchWorkflow(ParameterSweepWorkflow, MonitoringMixin):
    """
    Adaptive glitch workflow with profile-based intelligence.

    Execution phases:
    1. Profile Selection - Find best profile for target chip
    2. Known Parameters - Try documented successful parameters
    3. Coarse Sweep - Wide search if known params fail
    4. Fine Tuning - Refine around successes
    5. Success Mapping - Build complete success region map
    """

    def __init__(self, config: AdaptiveGlitchConfig):
        ParameterSweepWorkflow.__init__(
            self,
            name="Adaptive Glitch Attack",
            description="Profile-guided adaptive parameter search"
        )
        MonitoringMixin.__init__(self)

        self.config = config
        self.profile: Optional[GlitchProfile] = None

        # Device references
        self.glitcher_id: Optional[str] = None
        self.monitor_id: Optional[str] = None

        # Phase tracking
        self.current_phase = "initializing"
        self.phase_results = {}

    async def setup(self, device_pool) -> bool:
        """Setup devices and select best profile."""
        self.update_progress(0.0, "Setting up adaptive glitch workflow...")

        # Find glitcher and monitor (same as GlitchMonitorWorkflow)
        glitchers = device_pool.get_devices_by_role(DeviceRole.GLITCHER)
        if not glitchers:
            glitchers = device_pool.get_devices_by_capability("voltage_glitch")
            if not glitchers:
                glitchers = device_pool.get_devices_by_capability("emfi")

        if not glitchers:
            self.update_progress(0.0, "ERROR: No glitcher device found")
            return False

        self.glitcher_id = glitchers[0]
        device_pool.assign_role(self.glitcher_id, DeviceRole.GLITCHER)

        monitors = device_pool.get_devices_by_role(DeviceRole.MONITOR)
        if not monitors:
            monitors = device_pool.get_devices_by_capability("uart")

        if not monitors:
            self.update_progress(0.0, "ERROR: No monitor device found")
            return False

        self.monitor_id = monitors[0]
        device_pool.assign_role(self.monitor_id, DeviceRole.MONITOR)

        # Connect
        if not await device_pool.connect(self.glitcher_id):
            return False
        if not await device_pool.connect(self.monitor_id):
            return False

        # Select profile
        self.update_progress(2.0, "Selecting glitch profile...")
        self.profile = self._select_profile()

        if self.profile:
            self.update_progress(5.0, f"Using profile: {self.profile.name}")
            self.log(f"Selected profile: {self.profile.name}")
            self.log(f"  Chip family: {self.profile.chip_family}")
            self.log(f"  Target: {self.profile.target.value}")
            if self.profile.successful_params:
                self.log(f"  Known successful params: {len(self.profile.successful_params)}")
        else:
            self.update_progress(5.0, "No specific profile found, using generic search")
            self.log("No profile found - will do wide parameter sweep")

        return True

    def _select_profile(self) -> Optional[GlitchProfile]:
        """Select the best profile based on configuration."""
        # If profile name specified, use it
        if self.config.profile_name:
            return get_profile(self.config.profile_name)

        # If chip specified, find matching profiles
        if self.config.target_chip:
            profiles = find_profiles_for_chip(self.config.target_chip)

            if not profiles:
                return None

            # If attack target specified, filter by it
            if self.config.attack_target:
                profiles = [p for p in profiles if p.target == self.config.attack_target]

            # Return most specific profile
            if profiles:
                return profiles[0]

        return None

    async def execute(self, device_pool) -> WorkflowResult:
        """Execute adaptive glitch attack."""
        glitcher_backend = device_pool.get_backend(self.glitcher_id)
        monitor_backend = device_pool.get_backend(self.monitor_id)

        if not isinstance(glitcher_backend, GlitchBackend):
            raise RuntimeError("Glitcher device doesn't support glitching")
        if not isinstance(monitor_backend, BusBackend):
            raise RuntimeError("Monitor device doesn't support UART")

        # Start monitoring
        self.update_progress(10.0, "Starting UART monitor...")
        await self.start_monitoring(monitor_backend, interval_ms=50)

        iteration = 0

        try:
            # PHASE 1: Try known parameters (if available)
            if self.config.try_known_params_first and self.profile and self.profile.successful_params:
                self.current_phase = "known_params"
                self.update_progress(15.0, "Phase 1: Trying known successful parameters...")

                iteration = await self._try_known_parameters(
                    glitcher_backend,
                    self.profile.successful_params,
                    iteration
                )

                self.phase_results['known_params'] = {
                    'attempts': iteration,
                    'successes': len(self.successes)
                }

                # If we found successes, skip to fine tuning
                if self.successes:
                    self.update_progress(40.0, f"Found {len(self.successes)} successes with known params!")
                    if self.config.fine_tune_enabled:
                        self.current_phase = "fine_tune"
                        iteration = await self._fine_tune_parameters(glitcher_backend, iteration)
                    return self._build_result(iteration)

            # PHASE 2: Coarse sweep (if enabled and no successes yet)
            if self.config.coarse_sweep_enabled and not self.successes:
                self.current_phase = "coarse_sweep"
                self.update_progress(50.0, "Phase 2: Coarse parameter sweep...")

                # Determine search range
                if self.profile and self.profile.recommended_range:
                    search_range = self.profile.recommended_range
                    self.log(f"Using profile's recommended range")
                else:
                    # Generic wide search
                    search_range = self._get_generic_search_range()
                    self.log(f"Using generic wide search range")

                iteration = await self._coarse_sweep(
                    glitcher_backend,
                    search_range,
                    iteration
                )

                self.phase_results['coarse_sweep'] = {
                    'attempts': iteration - self.phase_results.get('known_params', {}).get('attempts', 0),
                    'successes': len(self.successes)
                }

            # PHASE 3: Fine tuning (if we have successes)
            if self.config.fine_tune_enabled and self.successes:
                self.current_phase = "fine_tune"
                self.update_progress(85.0, f"Phase 3: Fine-tuning around {len(self.successes)} successes...")

                iteration = await self._fine_tune_parameters(glitcher_backend, iteration)

                self.phase_results['fine_tune'] = {
                    'attempts': iteration - sum(
                        phase.get('attempts', 0) for phase in self.phase_results.values()
                    ),
                    'successes': len(self.successes)
                }

        finally:
            await self.stop_monitoring()

        return self._build_result(iteration)

    async def _try_known_parameters(
        self,
        glitcher: GlitchBackend,
        known_params: List,
        start_iteration: int
    ) -> int:
        """Try known successful parameters."""
        iteration = start_iteration

        for idx, params in enumerate(known_params):
            self.log(f"Trying known params #{idx+1}: width={params.width_ns}ns, offset={params.offset_ns}ns")

            config = GlitchConfig(
                width_ns=params.width_ns,
                offset_ns=params.offset_ns,
                repeat=params.repeat
            )
            glitcher.configure_glitch(config)

            # Multiple attempts
            for attempt in range(self.config.known_params_attempts):
                if self.is_cancelled:
                    return iteration

                iteration += 1
                self.update_progress(
                    15.0 + ((idx / len(known_params)) * 25.0),
                    f"Known params {idx+1}/{len(known_params)}, attempt {attempt+1}/{self.config.known_params_attempts}"
                )

                success = await self._try_glitch(glitcher, params.width_ns, params.offset_ns, iteration)
                if success:
                    self.log(f"✓ SUCCESS with known params!")

        return iteration

    async def _coarse_sweep(
        self,
        glitcher: GlitchBackend,
        search_range,
        start_iteration: int
    ) -> int:
        """Perform coarse parameter sweep."""
        iteration = start_iteration

        width_range = range(
            search_range.width_min,
            search_range.width_max + 1,
            search_range.width_step
        )
        offset_range = range(
            search_range.offset_min,
            search_range.offset_max + 1,
            search_range.offset_step
        )

        total = len(width_range) * len(offset_range) * self.config.coarse_attempts_per_setting
        current = 0

        for width in width_range:
            for offset in offset_range:
                if self.is_cancelled:
                    return iteration

                config = GlitchConfig(width_ns=width, offset_ns=offset)
                glitcher.configure_glitch(config)

                for attempt in range(self.config.coarse_attempts_per_setting):
                    iteration += 1
                    current += 1

                    self.update_progress(
                        50.0 + ((current / total) * 30.0),
                        f"Coarse sweep: {current}/{total} - {len(self.successes)} successes"
                    )

                    await self._try_glitch(glitcher, width, offset, iteration)

        return iteration

    async def _fine_tune_parameters(
        self,
        glitcher: GlitchBackend,
        start_iteration: int
    ) -> int:
        """Fine-tune around successful parameters."""
        iteration = start_iteration

        # Get unique success points to refine
        success_points = set()
        for success in self.successes:
            w = success['parameters']['width_ns']
            o = success['parameters']['offset_ns']
            success_points.add((w, o))

        self.log(f"Fine-tuning around {len(success_points)} unique success points")

        for idx, (width_center, offset_center) in enumerate(success_points):
            if self.is_cancelled:
                break

            self.log(f"Refining around width={width_center}ns, offset={offset_center}ns")

            # Fine grid around this success point
            width_range = range(
                max(0, width_center - self.config.fine_tune_range_ns),
                width_center + self.config.fine_tune_range_ns + 1,
                self.config.fine_tune_step_ns
            )
            offset_range = range(
                max(0, offset_center - self.config.fine_tune_range_ns),
                offset_center + self.config.fine_tune_range_ns + 1,
                self.config.fine_tune_step_ns
            )

            for width in width_range:
                for offset in offset_range:
                    if self.is_cancelled:
                        break

                    iteration += 1
                    self.update_progress(
                        85.0 + ((idx / len(success_points)) * 10.0),
                        f"Fine-tuning {idx+1}/{len(success_points)}"
                    )

                    config = GlitchConfig(width_ns=width, offset_ns=offset)
                    glitcher.configure_glitch(config)

                    for attempt in range(self.config.fine_tune_attempts):
                        await self._try_glitch(glitcher, width, offset, iteration)

        return iteration

    async def _try_glitch(
        self,
        glitcher: GlitchBackend,
        width: int,
        offset: int,
        iteration: int
    ) -> bool:
        """Try a single glitch and check for success."""
        # Clear monitor buffer
        self.get_monitor_data(clear=True)

        # Trigger glitch
        glitcher.trigger()

        # Wait for response
        await asyncio.sleep(self.config.timeout_ms / 1000.0)

        # Check for success patterns
        success_patterns = self.config.success_patterns
        if not success_patterns and self.profile:
            success_patterns = self.profile.success_patterns

        if success_patterns:
            for pattern in success_patterns:
                if self.check_monitor_for_pattern(pattern):
                    self.record_success(
                        parameters={'width_ns': width, 'offset_ns': offset},
                        details={
                            'phase': self.current_phase,
                            'output': self.get_monitor_data(clear=False).decode(errors='ignore')
                        }
                    )
                    return True

        return False

    def _get_generic_search_range(self):
        """Get generic wide search range for unknown chips."""
        from ..glitch_profiles import ParameterRange

        return ParameterRange(
            width_min=50,
            width_max=500,
            width_step=50,
            offset_min=1000,
            offset_max=10000,
            offset_step=500
        )

    def _build_result(self, total_iterations: int) -> WorkflowResult:
        """Build workflow result."""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0.0

        # Build success map (group by width for easier visualization)
        success_map = {}
        for success in self.successes:
            w = success['parameters']['width_ns']
            o = success['parameters']['offset_ns']
            if w not in success_map:
                success_map[w] = []
            success_map[w].append(o)

        return WorkflowResult(
            status=WorkflowStatus.COMPLETED if not self.is_cancelled else WorkflowStatus.CANCELLED,
            duration_seconds=duration,
            results={
                'total_iterations': total_iterations,
                'successes': self.successes,
                'success_count': len(self.successes),
                'success_rate': len(self.successes) / total_iterations if total_iterations > 0 else 0.0,
                'success_map': success_map,
                'phase_results': self.phase_results,
                'profile_used': self.profile.name if self.profile else None
            },
            metadata={
                'config': {
                    'target_chip': self.config.target_chip,
                    'profile': self.profile.name if self.profile else None,
                    'phases_executed': list(self.phase_results.keys())
                }
            }
        )

    async def cleanup(self, device_pool):
        """Cleanup after workflow."""
        if self._monitor_running:
            await self.stop_monitoring()

        if self.glitcher_id:
            glitcher_backend = device_pool.get_backend(self.glitcher_id)
            if isinstance(glitcher_backend, GlitchBackend):
                try:
                    glitcher_backend.disarm()
                except:
                    pass

        self.update_progress(100.0, "Cleanup complete")

    def log(self, message: str):
        """Log message (override to add to interaction log)."""
        print(f"[Adaptive] {message}")


# Convenience function
def create_adaptive_glitch_workflow(
    target_chip: str,
    success_patterns: List[bytes],
    attack_target: Optional[TargetType] = None,
    **kwargs
) -> AdaptiveGlitchWorkflow:
    """
    Create an adaptive glitch workflow with simplified parameters.

    Args:
        target_chip: Target chip name (e.g., "STM32F103C8")
        success_patterns: Byte patterns indicating success
        attack_target: Optional specific attack target (RDP_BYPASS, etc.)
        **kwargs: Additional AdaptiveGlitchConfig parameters

    Returns:
        AdaptiveGlitchWorkflow instance

    Example:
        workflow = create_adaptive_glitch_workflow(
            target_chip="STM32F103C8",
            success_patterns=[b'>>>', b'target halted'],
            attack_target=TargetType.RDP_BYPASS
        )
    """
    config = AdaptiveGlitchConfig(
        target_chip=target_chip,
        attack_target=attack_target,
        success_patterns=success_patterns,
        **kwargs
    )

    return AdaptiveGlitchWorkflow(config)
