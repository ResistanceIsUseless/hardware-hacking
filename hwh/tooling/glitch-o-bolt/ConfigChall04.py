######
# LEAVE THESE IMPORTS!
######
import time
import functions

from pyocd.core.helpers import ConnectHelper
from pyocd.flash.file_programmer import FileProgrammer

######
# config values
######

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

LENGTH = 50
REPEAT = 1
DELAY = 1

###
# name, enabled, string to match
###
conditions = [
    ['Start', False, '', 'start_chall_04'],
    ['Step1', False, '', 'step_1'],
    ['Step2', False, '', 'step_2'],
]

######
# Custom functions for conditions to trigger
######

def start_chall_04():
    functions.add_text(f"[Chall 4] enable uart switch then hold chall 4 button to load the challenge into memory.")
    functions.add_text(f"[Chall 4] once loaded hold 'boot 1' button and press 'reset' button to put in bootloader mode") 
    functions.add_text(f"[Chall 4] then press 'Step1'")

def step_1():
    functions.set_uart_switch(False)

    functions.add_text(f"\n[Chall 4] uploading firmware to ram... please wait")

    # Connect to the target board
    session = ConnectHelper.session_with_chosen_probe()
    session.open()

    # Optionally halt the target
    target = session.target
    target.halt()

    # Load binary file to specified address (e.g., 0x20000000)
    newFirmware = "/tmp/f103-analysis/h3/rootshell/shellcode-0xRoM.bin"
    programmer = FileProgrammer(session)
    programmer.program(newFirmware, base_address=0x20000000, file_format='bin')

    # Optionally resume execution
    target.resume()
    # Clean up
    session.close()

    with open(newFirmware, "rb") as f:
        original_data = f.read()

    # Connect to the target
    session = ConnectHelper.session_with_chosen_probe()
    session.open()

    target = session.target
    target.halt()

    # Read back the memory from the target
    read_data = target.read_memory_block8(0x20000000, len(original_data))

    # Compare
    if bytes(read_data) == original_data:
         functions.add_text(f"[+] Shellcode loaded successfully.")
    else:
         functions.add_text(f"[!] Mismatch detected. Shellcode may not have loaded correctly.")

    session.close()

    functions.change_baudrate(9600)
    functions.add_text(f"[Chall 4] hold buttons 'boot0' and 'boot1' and press the 'glitch' button")
    functions.add_text(f"[Chall 4] this single glitch will boot from SRAM")
    functions.add_text(f"[Chall 4] enable UART to access 'Low-level Shell' (might need to press reset)")
    functions.add_text(f"[Chall 4] then press 'Step2'")
    
def step_2():
    functions.send_uart_message("p") 
    time.sleep(1)
    functions.change_baudrate(115200)
