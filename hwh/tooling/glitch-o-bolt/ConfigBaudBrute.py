######
# LEAVE THESE IMPORTS!
######
import functions

######
# config values (you can edit these to fit your environment and use case)
######

# Serial port settings
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600

###
# name, enabled, string to match in output, function to run
# if string is blank ("") doesnt show toggle, just run button
###
conditions = [
    ["Next", False, "", "uart_up"],
    ["Prev", False, "", "uart_down"],
]

######
# Custom functions for conditions to trigger
######

baud_rates = [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 128000, 256000]


def uart_up():
    current_baud = functions.get_config_value("baud_rate")
    # Find the index of the current baud rate
    try:
        index = baud_rates.index(current_baud)
    except ValueError:
        # If current baud rate is not in the list, start from the lowest
        index = -1
    
    # Get the next higher baud rate (wrapping around if at the end)
    new_index = (index + 1) % len(baud_rates)
    new_baud = baud_rates[new_index]
    functions.change_baudrate(new_baud)
    functions.add_text(f"\n[Rate Up] {new_baud}")

def uart_down():
    current_baud = functions.get_config_value("baud_rate")
    # Find the index of the current baud rate
    try:
        index = baud_rates.index(current_baud)
    except ValueError:
        # If current baud rate is not in the list, start from the highest
        index = len(baud_rates)
    
    # Get the next lower baud rate (wrapping around if at the start)
    new_index = (index - 1) % len(baud_rates)
    new_baud = baud_rates[new_index]
    functions.change_baudrate(new_baud)
    functions.add_text(f"\n[Rate Down] {new_baud}")