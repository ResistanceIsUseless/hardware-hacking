"""
hwh TUI - Hardware Hacking Tool

Multi-device interface with device-based tabs.
Each connected device gets its own tab with all features.

Design:
- Main page shows detected devices
- Connect to device -> creates device tab
- Multiple devices can be connected simultaneously
- Split-screen layout for multi-device workflows (press 's')
"""

import asyncio
from typing import Dict, Optional, Type, List, Tuple

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Select, TabbedContent, TabPane, Footer, Header
from textual.binding import Binding

from ..detect import detect, DeviceInfo

# Import all panel types
from .panels.base import DevicePanel, GenericPanel, PanelCapability
from .panels.buspirate import BusPiratePanel
from .panels.bolt import BoltPanel
from .panels.tigard import TigardPanel
from .panels.faultycat import FaultyCatPanel
from .panels.tilink import TILinkPanel
from .panels.blackmagic import BlackMagicPanel
from .panels.uart_monitor import UARTMonitorPanel
from .panels.base import DeviceOutputMessage


class SplitPanelMirror(Container):
    """
    A mirror view that displays output from an existing panel.

    This avoids creating duplicate serial connections when showing
    the same device in split view. Instead of opening a new connection,
    it subscribes to output messages from the source panel.
    """

    def __init__(self, device_info: DeviceInfo, source_panel: "DevicePanel", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_info = device_info
        self.source_panel = source_panel
        self._log_widget = None

    def compose(self) -> ComposeResult:
        from textual.widgets import Log

        with Vertical():
            # Header
            with Horizontal(classes="panel-header"):
                yield Static(f"{self.device_info.name} (mirror)", classes="device-title")
                yield Static(f"Port: {self.device_info.port}", classes="device-port")

            # Output log - mirrors the source panel
            self._log_widget = Log(id=f"mirror-log-{id(self)}", classes="uart-log")
            self._log_widget.border_title = "output (mirrored)"
            yield self._log_widget

    async def on_mount(self) -> None:
        """Subscribe to output from the source panel when mounted"""
        # Register callback on source panel
        self.source_panel.on_output(self._on_source_output)

    def _on_source_output(self, text: str) -> None:
        """Handle output from the source panel"""
        if self._log_widget:
            try:
                self._log_widget.write(text)
            except Exception:
                pass

    async def disconnect(self) -> None:
        """Mirror doesn't own the connection, so nothing to disconnect"""
        pass


class SplitView(Container):
    """Split view container showing two device panels side by side"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.left_device_id: Optional[str] = None
        self.right_device_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="split-container"):
            # Left pane
            with Vertical(id="split-left", classes="split-pane"):
                yield Static("Select device for left pane", id="left-placeholder", classes="split-placeholder")

            # Divider
            yield Static("│", id="split-divider", classes="split-divider")

            # Right pane
            with Vertical(id="split-right", classes="split-pane"):
                yield Static("Select device for right pane", id="right-placeholder", classes="split-placeholder")


# Device VID:PID to panel class mapping
DEVICE_PANELS: Dict[tuple, Type[DevicePanel]] = {
    # Bus Pirate 5/6
    (0x1209, 0x7331): BusPiratePanel,

    # Curious Bolt
    (0xcafe, 0x4002): BoltPanel,

    # Bolt CTF (treated as UART monitor)
    (0xcafe, 0x4004): UARTMonitorPanel,

    # Tigard
    (0x0403, 0x6010): TigardPanel,

    # FaultyCat
    (0x2341, 0x8037): FaultyCatPanel,  # Arduino Micro based

    # Black Magic Probe
    (0x1d50, 0x6018): BlackMagicPanel,

    # TI MSP-FET
    (0x0451, 0xbef3): TILinkPanel,

    # Generic FTDI (could be many things)
    (0x0403, 0x6001): UARTMonitorPanel,

    # CH340 UART adapter
    (0x1a86, 0x7523): UARTMonitorPanel,

    # CP2102 UART adapter
    (0x10c4, 0xea60): UARTMonitorPanel,
}


class HwhApp(App):
    """
    hwh TUI Application

    Architecture:
    - Devices tab shows all detected devices
    - Each connected device gets its own tab
    - Tabs contain device-specific panels with all features
    """

    CSS_PATH = "style.tcss"
    TITLE = "hwh - Hardware Hacking Toolkit"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_devices", "Refresh"),
        Binding("d", "show_devices", "Devices"),
        Binding("s", "toggle_split", "Split"),
        Binding("c", "show_coordination", "Coordination"),
        Binding("escape", "show_devices", "Discovery"),
        Binding("?", "show_help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.available_devices: Dict[str, DeviceInfo] = {}
        self.connected_panels: Dict[str, DevicePanel] = {}
        self.split_panels: Dict[str, DevicePanel] = {}  # Panels created for split view
        self._tab_counter = 0
        self._split_view_active = False

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent(id="main-tabs"):
            # Devices tab - always present
            with TabPane("Devices", id="tab-devices"):
                yield from self._build_devices_page()

        yield Footer()

    def _build_devices_page(self) -> ComposeResult:
        """Build the device selection page"""
        with Vertical(id="devices-page"):
            yield Static("hwh - Hardware Hacking Toolkit", id="app-title")
            yield Static("Detected Devices:", classes="section-title")

            # Device list container
            yield ScrollableContainer(id="device-list")

            # Control buttons
            with Horizontal(classes="button-row"):
                yield Button("Refresh Devices", id="btn-refresh", classes="btn-action")
                yield Button("Add Manual Device", id="btn-add-manual", classes="btn-action")

    async def on_ready(self) -> None:
        """Initialize application"""
        await self.refresh_device_list()

    async def action_refresh_devices(self) -> None:
        """Refresh device list action"""
        await self.refresh_device_list()

    async def action_show_devices(self) -> None:
        """Switch to devices tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "tab-devices"

    async def action_show_help(self) -> None:
        """Show help"""
        self.notify("hwh - Hardware Hacking Toolkit\nPress 'q' to quit, 'r' to refresh, 's' for split view, 'c' for coordination")

    async def action_show_coordination(self) -> None:
        """Show coordination panel for multi-device operations"""
        if len(self.connected_panels) < 2:
            self.notify("Connect at least 2 devices for coordination mode", severity="warning")
            return

        tabs = self.query_one("#main-tabs", TabbedContent)

        # Check if coordination tab already exists
        try:
            tabs.active = "tab-coordination"
            return
        except Exception:
            pass

        # Create coordination tab
        await self._create_coordination_tab()

    async def _create_coordination_tab(self) -> None:
        """Create a coordination tab for multi-device operations"""
        tabs = self.query_one("#main-tabs", TabbedContent)

        pane = TabPane("Coordination", id="tab-coordination")
        await tabs.add_pane(pane)

        # Build coordination content
        coord_content = Vertical(id="coordination-content")
        await pane.mount(coord_content)

        # Header
        await coord_content.mount(Static("Multi-Device Coordination", classes="section-title"))
        await coord_content.mount(Static("Coordinate operations across multiple connected devices", classes="section-subtitle"))

        # Connected devices summary
        devices_summary = Vertical(id="coord-devices", classes="coord-section")
        await coord_content.mount(devices_summary)
        await devices_summary.mount(Static("Connected Devices:", classes="coord-label"))

        for device_id, panel in self.connected_panels.items():
            device_info = self.available_devices.get(device_id)
            if device_info:
                caps = ", ".join(device_info.capabilities[:3])
                await devices_summary.mount(Static(f"  • {device_info.name} [{caps}]", classes="coord-device"))

        # Coordination actions
        actions_section = Vertical(id="coord-actions", classes="coord-section")
        await coord_content.mount(actions_section)
        await actions_section.mount(Static("Coordination Actions:", classes="coord-label"))

        # Create button row (can't use context manager outside compose())
        button_row = Horizontal(classes="coord-buttons")
        await actions_section.mount(button_row)
        await button_row.mount(Button("Glitch + Monitor", id="coord-glitch-monitor", classes="btn-coord"))
        await button_row.mount(Button("Parallel Read", id="coord-parallel-read", classes="btn-coord"))
        await button_row.mount(Button("Sync Triggers", id="coord-sync-triggers", classes="btn-coord"))

        # Switch to coordination tab
        tabs.active = "tab-coordination"
        self.notify("Coordination mode - select an operation")

    async def action_toggle_split(self) -> None:
        """Toggle split view mode"""
        tabs = self.query_one("#main-tabs", TabbedContent)

        if self._split_view_active:
            # Remove split view tab
            try:
                await tabs.remove_pane("tab-split")
                self._split_view_active = False
                # Clean up split panels
                for panel in self.split_panels.values():
                    await panel.disconnect()
                self.split_panels.clear()
                self.notify("Split view closed")
            except Exception:
                pass
        else:
            # Check if we have at least 2 connected devices
            if len(self.connected_panels) < 2:
                self.notify("Connect at least 2 devices for split view", severity="warning")
                return

            # Create split view tab
            await self._create_split_view()
            self._split_view_active = True

    async def _create_split_view(self) -> None:
        """Create a split view with device selectors"""
        tabs = self.query_one("#main-tabs", TabbedContent)

        # Create the split view pane
        pane = TabPane("Split View", id="tab-split")
        await tabs.add_pane(pane)

        # Build split view content - create widgets directly, no context manager
        split_content = Vertical(id="split-content")
        await pane.mount(split_content)

        # Device selector row
        selector_row = Horizontal(id="split-selectors", classes="split-selector-row")
        await split_content.mount(selector_row)

        # Build device options from connected panels
        device_options = [(device_id, info.name) for device_id, info in self.available_devices.items()
                         if device_id in self.connected_panels]

        # Left pane selector
        await selector_row.mount(Static("Left:", classes="split-label"))
        left_select = Select(
            [(name, dev_id) for dev_id, name in device_options],
            id="select-left",
            classes="split-select",
            prompt="Select device"
        )
        await selector_row.mount(left_select)

        # Right pane selector
        await selector_row.mount(Static("Right:", classes="split-label"))
        right_select = Select(
            [(name, dev_id) for dev_id, name in device_options],
            id="select-right",
            classes="split-select",
            prompt="Select device"
        )
        await selector_row.mount(right_select)

        # Main split container
        split_container = Horizontal(id="split-container", classes="split-container")
        await split_content.mount(split_container)

        # Create left and right panes with divider
        left_pane = Vertical(id="split-left", classes="split-pane")
        divider = Static("│" * 50, classes="split-divider")  # Vertical line
        right_pane = Vertical(id="split-right", classes="split-pane")

        await split_container.mount(left_pane)
        await split_container.mount(divider)
        await split_container.mount(right_pane)

        # Add placeholders
        await left_pane.mount(Static("Select a device above", classes="split-placeholder"))
        await right_pane.mount(Static("Select a device above", classes="split-placeholder"))

        # Switch to split view
        tabs.active = "tab-split"
        self.notify("Split view opened - select devices above")

    async def _update_split_pane(self, pane_id: str, device_id: str) -> None:
        """Update a split pane with a device panel or mirror"""
        try:
            pane = self.query_one(f"#{pane_id}", Vertical)
            await pane.remove_children()

            device_info = self.available_devices.get(device_id)
            if not device_info:
                await pane.mount(Static("Device not found", classes="split-placeholder"))
                return

            # Clean up old panel/mirror in this pane
            old_panel = self.split_panels.get(pane_id)
            if old_panel:
                await old_panel.disconnect()

            # Check if this device already has a connected panel
            existing_panel = self.connected_panels.get(device_id)

            if existing_panel:
                # Device is already connected - create a mirror view instead
                # This avoids creating duplicate serial connections
                mirror = SplitPanelMirror(
                    device_info=device_info,
                    source_panel=existing_panel,
                    id=f"mirror-{pane_id}-{device_id}"
                )
                self.split_panels[pane_id] = mirror
                await pane.mount(mirror)
                self.notify(f"Mirroring {device_info.name} output")

            else:
                # No existing panel - create new one with its own connection
                panel_class = self._get_panel_class(device_info)
                panel = panel_class(device_info, self, id=f"split-{pane_id}-{device_id}")
                self.split_panels[pane_id] = panel
                await pane.mount(panel)
                await panel.connect()

        except Exception as e:
            self.notify(f"Error updating split pane: {e}", severity="error")

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle device selection in split view"""
        select_id = event.select.id
        if not select_id:
            return

        device_id = str(event.value) if event.value else None
        if not device_id:
            return

        if select_id == "select-left":
            await self._update_split_pane("split-left", device_id)
        elif select_id == "select-right":
            await self._update_split_pane("split-right", device_id)

    async def refresh_device_list(self) -> None:
        """Detect devices and update the list"""
        # Detect devices
        detected = detect()

        # Convert to our format
        self.available_devices = {}
        for device_id, device_info in detected.items():
            self.available_devices[device_id] = device_info

        # Update UI
        await self._update_device_list_ui()

        self.notify(f"Found {len(self.available_devices)} device(s)")

    async def _update_device_list_ui(self) -> None:
        """Update the device list in the UI"""
        try:
            device_list = self.query_one("#device-list", ScrollableContainer)
            await device_list.remove_children()

            if not self.available_devices:
                await device_list.mount(
                    Static("No devices detected. Connect a device and click Refresh.", classes="no-devices")
                )
                return

            # Add device entries - compact single-line format
            for device_id, device_info in self.available_devices.items():
                is_connected = device_id in self.connected_panels

                # Create compact device entry
                entry = Horizontal(classes="device-entry")
                await device_list.mount(entry)

                # Status indicator (● connected, ○ disconnected)
                status_symbol = "●" if is_connected else "○"
                status_class = "status-connected" if is_connected else "status-disconnected"
                await entry.mount(Static(status_symbol, classes=f"status-indicator {status_class}"))

                # Device name
                await entry.mount(Static(device_info.name, classes="device-name"))

                # Port path
                await entry.mount(Static(device_info.port or "N/A", classes="device-port"))

                # Capabilities (abbreviated)
                caps = ", ".join(device_info.capabilities[:4]) if device_info.capabilities else "-"
                if len(device_info.capabilities) > 4:
                    caps += "..."
                await entry.mount(Static(f"[{caps}]", classes="device-caps"))

                # Connect/Disconnect button
                if is_connected:
                    btn = Button("Disconnect", id=f"disconnect-{device_id}", classes="btn-disconnect")
                else:
                    btn = Button("Connect", id=f"connect-{device_id}", classes="btn-connect")
                await entry.mount(btn)

        except Exception as e:
            self.notify(f"Error updating device list: {e}", severity="error")

    def _get_panel_class(self, device_info: DeviceInfo) -> Type[DevicePanel]:
        """Get the appropriate panel class for a device"""
        key = (device_info.vid, device_info.pid)

        if key in DEVICE_PANELS:
            return DEVICE_PANELS[key]

        # Check capabilities for generic panel selection
        if device_info.capabilities:
            caps = [c.lower() for c in device_info.capabilities]
            if "glitch" in caps:
                return BoltPanel
            if "swd" in caps or "jtag" in caps:
                return TigardPanel
            if "spi" in caps or "i2c" in caps:
                return BusPiratePanel

        # Default to UART monitor for unknown serial devices
        return UARTMonitorPanel

    async def connect_device(self, device_id: str) -> None:
        """Connect to a device and create its tab"""
        if device_id in self.connected_panels:
            self.notify(f"Already connected to {device_id}")
            return

        device_info = self.available_devices.get(device_id)
        if not device_info:
            self.notify(f"Device not found: {device_id}", severity="error")
            return

        try:
            # Get appropriate panel class
            panel_class = self._get_panel_class(device_info)

            # Create panel instance
            self._tab_counter += 1
            tab_id = f"tab-device-{self._tab_counter}"

            panel = panel_class(device_info, self, id=f"panel-{device_id}")

            # Store panel reference
            self.connected_panels[device_id] = panel

            # Add tab to tabbed content
            tabs = self.query_one("#main-tabs", TabbedContent)

            # Create tab pane with panel
            pane = TabPane(device_info.name, id=tab_id)
            await tabs.add_pane(pane)
            await pane.mount(panel)

            # Connect to device
            success = await panel.connect()

            if success:
                # Switch to new tab
                tabs.active = tab_id
                self.notify(f"Connected to {device_info.name}")
            else:
                # Remove tab on failure
                await tabs.remove_pane(tab_id)
                del self.connected_panels[device_id]
                self.notify(f"Failed to connect to {device_info.name}", severity="error")

            # Update device list
            await self._update_device_list_ui()

        except Exception as e:
            self.notify(f"Connection error: {e}", severity="error")

    async def disconnect_device(self, device_id: str) -> None:
        """Disconnect from a device and remove its tab"""
        panel = self.connected_panels.get(device_id)
        if not panel:
            return

        try:
            # Disconnect panel
            await panel.disconnect()

            # Find and remove tab
            tabs = self.query_one("#main-tabs", TabbedContent)
            for pane in tabs.query(TabPane):
                if panel in pane.query("*"):
                    await tabs.remove_pane(pane.id)
                    break

            # Remove from connected panels
            del self.connected_panels[device_id]

            # Update device list
            await self._update_device_list_ui()

            self.notify(f"Disconnected from {panel.device_info.name}")

        except Exception as e:
            self.notify(f"Disconnect error: {e}", severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "btn-refresh":
            await self.refresh_device_list()

        elif button_id == "btn-add-manual":
            self.notify("Manual device addition not yet implemented")

        elif button_id.startswith("connect-"):
            device_id = button_id.replace("connect-", "")
            await self.connect_device(device_id)

        elif button_id.startswith("disconnect-"):
            device_id = button_id.replace("disconnect-", "")
            await self.disconnect_device(device_id)


def run_tui():
    """Launch the TUI"""
    app = HwhApp()
    app.run()


if __name__ == "__main__":
    run_tui()
