######
# DEMO CONFIG - No hardware required
# This demonstrates the TUI functionality without connected devices
######
import functions
import random
from textual.widgets import Log

######
# config values
######

# Serial port settings (won't connect, just for display)
SERIAL_PORT = "/dev/null"
BAUD_RATE = 115200
UART_NEWLINE = "\n"

LENGTH = 42
REPEAT = 10
DELAY = 50

###
# ^ = pullup, v = pulldown, - = disabled
###
triggers = [
    ["^", True],  #0 - Pull-up enabled
    ["-", False], #1 - Disabled
    ["v", True],  #2 - Pull-down enabled
    ["-", False], #3
    ["-", False], #4
    ["-", False], #5
    ["-", False], #6
    ["-", False], #7
]

###
# name, enabled, string to match in output, function to run
# if string is blank ("") doesnt show toggle, just run button
###
conditions = [
    ["Rand", False, "", "random_glitch_params"],  # Button only - randomize params
    ["Cycle", False, "", "cycle_triggers"],       # Button only - cycle trigger states
    ["Demo", False, "", "show_demo_info"],        # Button only - show info
]

######
# Custom functions for conditions to trigger
######

def random_glitch_params():
    """Randomize glitch parameters to demonstrate UI updates"""
    NewLen = random.randint(1, 100)
    NewRep = random.randint(1, 200)
    NewDel = random.randint(0, 500)

    functions.set_config_value("length", NewLen)
    functions.set_config_value("repeat", NewRep)
    functions.set_config_value("delay", NewDel)

    functions.add_text(f"🎲 Randomized: length={NewLen}, repeat={NewRep} (~{NewRep*8.3:.0f}ns), delay={NewDel}")
    functions.log_message(f"[DEMO] Random params: L={NewLen} R={NewRep} D={NewDel}")

def cycle_triggers():
    """Cycle all trigger states through ^, v, - sequence"""
    for i in range(8):
        current_symbol = functions.get_trigger_string(i)
        cycle = ["^", "v", "-"]
        next_symbol = cycle[(cycle.index(current_symbol) + 1) % len(cycle)]
        functions.set_trigger_string(i, next_symbol)

    functions.add_text("🔄 Cycled all triggers: ^ → v → - → ^")
    functions.log_message("[DEMO] Cycled trigger states")

def show_demo_info():
    """Display demo information"""
    Len = functions.get_config_value("length")
    Rep = functions.get_config_value("repeat")
    Del = functions.get_config_value("delay")

    glitch_ns = Rep * 8.3
    delay_ns = Del * 8.3

    functions.add_text("=" * 50)
    functions.add_text("📊 DEMO MODE - Current Configuration")
    functions.add_text("=" * 50)
    functions.add_text(f"Glitch Parameters:")
    functions.add_text(f"  • length: {Len}")
    functions.add_text(f"  • repeat: {Rep} cycles ({glitch_ns:.1f}ns)")
    functions.add_text(f"  • delay:  {Del} cycles ({delay_ns:.1f}ns)")
    functions.add_text("")
    functions.add_text("TUI Controls:")
    functions.add_text("  • Tab: Move between controls")
    functions.add_text("  • +/- Buttons: Adjust values")
    functions.add_text("  • Switches: Toggle triggers/conditions")
    functions.add_text("  • 'Rand' button: Randomize parameters")
    functions.add_text("  • 'Cycle' button: Cycle trigger states")
    functions.add_text("=" * 50)
    functions.log_message("[DEMO] Displayed info")
