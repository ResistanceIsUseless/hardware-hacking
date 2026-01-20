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
SERIAL_PORT = "/dev/ttyACM3"
BAUD_RATE = 115200

LENGTH = 10
REPEAT = 5
DELAY = 100

###
# ^ = pullup, v = pulldown
###
triggers = [
    ["-", False], #0
    ["-", False], #1
    ["-", False], #2
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
    ["user", False, "Router login:", "send_username"],
    ["pass", False, "Password", "send_password"],
    ["enter", False, "press Enter", "send_return"],
]

######
# Custom functions for conditions to trigger
######

def send_username():
    functions.send_uart_message("root")  
    functions.add_text("[auto] $> root")    

# uncomment the following to use a password list!
#with open("passwords.txt", "r") as f:
#    password_list = [line.strip() for line in f if line.strip()]

password_list = ["root", "password", "123456", "qwerty", "admin", "letmein"]
current_password_index = 0

def send_password():
    global password_list, current_password_index
    
    passCount = len(password_list)
    # Get the current password
    password = password_list[current_password_index]
    
    # Send the password and update UI
    functions.send_uart_message(password)  
    functions.add_text(f"[pass {current_password_index} / {passCount}] $> {password}")
    # Move to the next password (wrap around if at end of list)
    current_password_index = (current_password_index + 1) % len(password_list)

def send_return():
    functions.send_uart_message(" ")    