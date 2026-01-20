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

LENGTH = 6000
REPEAT = 0
DELAY = 1098144

###
# ^ = pullup, v = pulldown
###
triggers = [
    ['-', False],  #0
    ['v', True],  #1
    ['-', False],  #2
    ['-', False],  #3
    ['-', False],  #4
    ['-', False],  #5
    ['-', False],  #6
    ['-', False],  #7
]

###
# name, enabled, string to match
###
conditions = [
    ['Flag', True, 'ctf', 'stop_glitching'],
]

######
# Custom functions for conditions to trigger
######

def stop_glitching():
        elapsed = functions.get_glitch_elapsed()
        functions.glitching_switch(False)
        functions.add_text(f"[auto] glitching stopped (elapsed: {elapsed})") 
