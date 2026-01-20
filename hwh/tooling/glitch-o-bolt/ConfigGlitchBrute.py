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

LENGTH = 1
REPEAT = 1
DELAY = 1

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
    ["pt1", True, "Hold one of", "start_chal_02"], # requires bolt output gpio pin 0 -> challenge board chall 2 button
    ["pt2", True, "Starting challenge 2", "glitched_too_far"],
    ["std", True, "1000000", "perform_glitch"]
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
    #functions.execute_condition_action("glitched_too_far")

increment_delay = True
increment_length = True
inc_delay_amount = 100
inc_repeat_amount = 100
inc_length_amount = 100  

def perform_glitch():
    global increment_delay, increment_length
    global inc_delay_aamount, inc_repeat_amount, inc_length_amount
    
    
    if increment_delay:
        to_increment = "delay"
        increment_amount = inc_delay_amount
        increment_delay = False
    else:
        if increment_length:
            to_increment = "length"
            increment_amount = inc_length_amount
            increment_length = False
            increment_delay = True
        else:
            to_increment = "repeat"
            increment_amount = inc_repeat_amount
            increment_length = True
            increment_delay = True
    
    current_val = functions.get_config_value(to_increment)
    new_val = current_val + increment_amount
    functions.set_config_value(to_increment, new_val)

    functions.add_text(f"[auto] incrementing: {to_increment}")
    
    Len = functions.get_config_value("length")
    Rep = functions.get_config_value("repeat")
    Del = functions.get_config_value("delay")
    functions.start_glitch(Len, Rep, Del)
    
def glitched_too_far():
    global increment_delay, increment_length
    global inc_delay_amount, inc_repeat_amount, inc_length_amount
    
    # Determine which value to decrement based on current state
    if increment_delay:
        if increment_length:
            to_decrement = "repeat"
            current_inc_amount = inc_repeat_amount
        else:
            to_decrement = "length"
            current_inc_amount = inc_length_amount
    else:
        to_decrement = "delay"
        current_inc_amount = inc_delay_amount
    
    # Get current value and decrement it
    current_val = functions.get_config_value(to_decrement)
    new_val = current_val - current_inc_amount 
    functions.set_config_value(to_decrement, new_val)
    
    # Update the increment amount for next time
    if current_inc_amount == 100:
        new_inc_amount = 10
    elif current_inc_amount == 10:
        new_inc_amount = 1
    else:
        new_inc_amount = current_inc_amount  # keep as is if not 100 or 10
    
    # Update the correct increment amount variable
    if to_decrement == "delay":
        inc_delay_amount = new_inc_amount
    elif to_decrement == "length":
        inc_length_amount = new_inc_amount
    elif to_decrement == "repeat":
        inc_repeat_amount = new_inc_amount

    functions.add_text(f"[auto] decrementing: {to_decrement}")