"""
hwh TUI Device Panels

Each panel represents a connected device and its capabilities.
Panels are created dynamically when devices connect.
"""

from .base import DevicePanel, PanelCapability
from .buspirate import BusPiratePanel
from .bolt import BoltPanel
from .tigard import TigardPanel
from .faultycat import FaultyCatPanel
from .tilink import TILinkPanel
from .blackmagic import BlackMagicPanel
from .uart_monitor import UARTMonitorPanel
from .logic_analyzer import LogicAnalyzerWidget

__all__ = [
    "DevicePanel",
    "PanelCapability",
    "BusPiratePanel",
    "BoltPanel",
    "TigardPanel",
    "FaultyCatPanel",
    "TILinkPanel",
    "BlackMagicPanel",
    "UARTMonitorPanel",
    "LogicAnalyzerWidget",
]
