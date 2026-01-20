######
# LEAVE THESE IMPORTS!
######
import functions
import random
from textual.widgets import Log

######
# config values (you can edit these to fit your environment and use case)
######

# Serial port settings
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
UART_NEWLINE = "\n" # non-standard, default is \r\n

LENGTH = 10
REPEAT = 5
DELAY = 100

###
# ^ = pullup, v = pulldown
###
triggers = [
    ["^", True],  #0
    ["-", False], #1
    ["v", True],  #2
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
	["No01", False, "WillNeverMatch01", ""],
	["No02", False, "WillNeverMatch02", ""],
    ["Heigh", False, "", "get_scroll_height"],
    ["AllTg", False, "", "toggle_all"],
    ["Trigr", False, "", "change_all_triggers"],
    ["Value", False, "", "random_values"],
    ['9600', False, '', 'change_baud_9600'],
    ['11520', False, '', 'change_baud_115200'],
]

######
# Custom functions for conditions to trigger
######

def get_scroll_height():
    if functions.app_instance:
        text_widget = functions.app_instance.query_one(".scrollable_log", Log)  # Find the scrollable text area
        height = text_widget.scrollable_content_region.height  # Get its height
                # Ensure the text is a string and append it to the Log widget
        random_number = random.randint(1, 100)
        new_text = f"[CONDITION] Scrollable height: {height} and Random Number: {random_number}"
        functions.add_text(new_text)
        functions.log_message(new_text)  # Log the value
    else:
        functions.log_message("App instance not set!")  # Debugging in case it's called too early

def toggle_all():
	TriggersStatus = functions.get_trigger_value(0)
	if TriggersStatus is True:
		for i in range(8):
			functions.set_trigger_value(i, False)
		for i in range( len(conditions) ):
			functions.set_condition_value(i, False)	
	else:
		for i in range(8):
			functions.set_trigger_value(i, True)
		for i in range( len(conditions) ):
			functions.set_condition_value(i, True)	

def change_all_triggers():
	for i in range(8):
		current_symbol = functions.get_trigger_string(i)
		cycle = ["^", "v", "-"]
		next_symbol = cycle[(cycle.index(current_symbol) + 1) % len(cycle)]
		functions.set_trigger_string(i, next_symbol)

def random_values():
	functions.glitching_switch(False)

	OrigLen = functions.get_config_value("length")
	OrigRep = functions.get_config_value("repeat")
	OrigDel = functions.get_config_value("delay")

	NewLen = random.randint(1, 100)
	NewRep = random.randint(1, 100)
	NewDel = random.randint(1, 100)

	functions.set_config_value("length", NewLen)
	functions.set_config_value("repeat", NewRep)
	functions.set_config_value("delay", NewDel)

	functions.add_text(f"[UPDATED] length ({OrigLen} -> {NewLen}), repeat ({OrigRep} -> {NewRep}), delay ({OrigDel} -> {NewDel})")

def change_baud_9600():
    functions.change_baudrate(9600)
    functions.set_uart_switch()

def change_baud_115200():
    functions.change_baudrate(115200)
    functions.set_uart_switch(False)