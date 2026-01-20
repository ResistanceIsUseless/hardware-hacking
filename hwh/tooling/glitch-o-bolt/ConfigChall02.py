######
# LEAVE THESE IMPORTS!
######
import functions
import random
from textual.widgets import Log

######
# config values
######

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

LENGTH = 42
REPEAT = 1
DELAY = 0

###
# ^ = pullup, v = pulldown
###
triggers = [
    ['-', False],  #0
    ['-', False],  #1
    ['-', False],  #2
    ['-', False],  #3
    ['-', False],  #4
    ['-', False],  #5
    ['-', False],  #6
    ['-', False],  #7
]

###
# name, enabled, string to match in output, function to run
# if string is blank ("") doesnt show toggle, just run button
###
conditions = [
    ["Flag", True,  "ctf", "stop_glitching"],
    ["Chal2", True, "Hold one of", "start_chal_02"] # requires bolt output gpio pin 0 -> challenge board chall 2 button
]

######
# Custom functions for conditions to trigger
######

def stop_glitching():
	elapsed = functions.get_glitch_elapsed()
	functions.glitching_switch(False)
	functions.add_text(f"[auto] glitching stopped (elapsed: {elapsed})")    

def start_chal_02():
    functions.run_output_high(0, 30000000) ## can also run_output_low() if need too