import sys
import os
import re
import time
import serial
import importlib
from scope import Scope
from FaultycatModules import Worker
from textual.widgets import Button, Input, Switch
from textual.containers import Vertical

import asyncio
import functions

DEBUG_MODE = True

app_instance = None  # Global variable to store the app instance
text_area = None     # Store global reference to scrollable text area
config = None        # dynamic loading of config file
log_time = 0         # timestamp for logfile
glitch_time = 0      # timestamp for when glitching started

# FaultyCat Variables
DEFAULT_FAULTY_COMPORT = "/dev/ttyACM0"
faulty_worker = Worker.FaultyWorker()

try:
    s = Scope()
except IOError:
    s = None
    print("Warning: Scope not connected, running in simulation mode")

def set_config(cfg):
    global config
    config = cfg

def set_app_instance(app):
    """Store the app instance for UART access"""
    global app_instance
    app_instance = app

def log_message(message):
    if DEBUG_MODE:  
        with open("debug.log", "a") as log_file:
            log_file.write(message + "\n")

def set_log_time(value):
    global log_time
    log_time = value

def set_glitch_time(value):
    global glitch_time
    glitch_time = value

def get_config_value(name: str) -> int:
    """Return the latest value of the given config variable, and create them if they don't exist."""
    if name == "length":
        if not hasattr(config, "LENGTH"):
            config.LENGTH = 0  # Default value if not set
        return config.LENGTH
    elif name == "repeat":
        if not hasattr(config, "REPEAT"):
            config.REPEAT = 0  # Default value if not set
        return config.REPEAT
    elif name == "serial_port":
        if not hasattr(config, "SERIAL_PORT"):
            config.SERIAL_PORT = "/dev/ttyUSB0"  # Default value if not set
        return config.SERIAL_PORT
    elif name == "baud_rate":
        if not hasattr(config, "BAUD_RATE"):
            config.BAUD_RATE = 115200  # Default value if not set
        return config.BAUD_RATE
    elif name == "delay":
        if not hasattr(config, "DELAY"):
            config.DELAY = 0  # Default value if not set
        return config.DELAY
    elif name == "log_time":
        return log_time  # Return the module variable directly
    elif name == "glitch_time":
        return glitch_time  # Return the module variable directly
    elif name == "conFile":
        if not hasattr(config, "CONFILE"):
            config.CONFILE = "config.py"  # Or any suitable default
        return config.CONFILE
    elif name == "uart_output_enabled":
        if not hasattr(config, "UART_OUTPUT_ENABLED"):
            config.UART_OUTPUT_ENABLED = False  # Default to disabled
        return config.UART_OUTPUT_ENABLED
    elif name == "uart_newline":
        if not hasattr(config, "UART_NEWLINE"):
            config.UART_NEWLINE = "\r\n"  # Default value if not set
        return config.UART_NEWLINE
    elif name.startswith("trigger_"):
        if "_value" in name:
            index = int(name.split('_')[1])
            return config.triggers[index][0]
        elif "_state" in name:
            index = int(name.split('_')[1])
            return config.triggers[index][1]
    else:
        return 0  # Default fallback for unknown names

def set_config_value(name: str, value):
    """Set the value of a config variable and update the UI if applicable."""
    attr_name = name.upper()

    # Create the attribute if it doesn't exist
    if not hasattr(config, attr_name):
        setattr(config, attr_name, value)
    else:
        setattr(config, attr_name, value)

    # Safely update corresponding input field if it exists
    try:
        input_field = app_instance.query_one(f"#{name}_input")
        input_field.value = str(value)
    except Exception:
        # No input field exists for this config; ignore
        pass

    # Safely update status box row if possible
    try:
        update_status_box(app_instance, name, value)
    except Exception:
        pass

    # Refresh UI
    try:
        app_instance.refresh()
    except Exception:
        pass

def get_condition_string(index):
    """Returns the string from the triggers list at the given index."""
    if 0 <= index < len(config.conditions):
        return config.conditions[index][0]  # Return the string value
    else:
        raise IndexError("Index out of range")

def get_condition_value(index):
    """Returns the value from the triggers list at the given index."""
    if 0 <= index < len(config.conditions):
        return config.conditions[index][1]  # Return the boolean value
    else:
        raise IndexError("Index out of range")

def set_condition_value(index: int, value: bool) -> None:
    """Update switch state in config"""
    if 0 <= index < len(config.conditions):
        if app_instance.query(f"#condition_switch_{index}"):
            switch = app_instance.query_one(f"#condition_switch_{index}", Switch)  
            switch.value = value  # Force turn off
    else:
        raise IndexError("Index out of range")

def ensure_triggers_exist():
    if not hasattr(config, "triggers") or not config.triggers or len(config.triggers) < 8:
        config.triggers = [["-", False] for _ in range(8)]

def get_trigger_string(index):
    """Returns the string from the triggers list at the given index."""
    if 0 <= index < len(config.triggers):
        return config.triggers[index][0]  # Return the string value
    else:
        raise IndexError("Index out of range")

def get_trigger_value(index):
    """Returns the value from the triggers list at the given index."""
    if 0 <= index < len(config.triggers):
        return config.triggers[index][1]  # Return the boolean value
    else:
        raise IndexError("Index out of range")

def set_trigger_value(index, value):
    if 0 <= index < len(config.triggers):
        switch = app_instance.query_one(f"#trigger_switch_{index}", Switch)  
        switch.value = value  # Force turn off
    else:
        raise IndexError("Index out of range")

def set_trigger_string(index: int, value: str):
    # Validate the input value
    valid_values = ["^", "v", "-"]
    if value not in valid_values:
        raise ValueError(f"Invalid trigger value. Must be one of {valid_values}")

    # Update config
    config.triggers[index][0] = value
    config.triggers[index][1] = False

    # Update the symbol display in the UI
    symbol_widget = app_instance.query_one(f"#trigger_symbol_{index}")
    symbol_widget.update(value)

    # Update the switch in the UI
    switch_widget = app_instance.query_one(f"#trigger_switch_{index}")
    switch_widget.value = False

def toggle_trigger(self, index: int):
    current_symbol = config.triggers[index][0]
    cycle = ["^", "v", "-"]
    next_symbol = cycle[(cycle.index(current_symbol) + 1) % len(cycle)]

    # Update config
    config.triggers[index][0] = next_symbol
    config.triggers[index][1] = False

    # Update the symbol display in the UI
    symbol_widget = self.query_one(f"#trigger_symbol_{index}")
    symbol_widget.update(next_symbol)

    # Update the switch in the UI
    switch_widget = self.query_one(f"#trigger_switch_{index}")
    switch_widget.value = False
    log_message("next symbol: "+next_symbol)

def set_uart_switch(state: bool | None = None) -> None:
    switch_uart = app_instance.query_one("#uart_switch")
    if state is None:
        switch_uart.value = not switch_uart.value  # Toggle
    else:
        switch_uart.value = state  # Set to specific state

def modify_value(variable_name: str, amount: int) -> int:
    """
    Modify a global variable by a given amount.
    
    Args:
        variable_name (str): The name of the variable to modify.
        amount (int): The amount to increment or decrement.

    Returns:
        int: The updated value.
    """
    global config  # Ensure we modify the variables from config.py

    if variable_name == "length":
        config.LENGTH += amount
        return config.LENGTH
    elif variable_name == "repeat":
        config.REPEAT += amount
        return config.REPEAT
    elif variable_name == "delay":
        config.DELAY += amount
        return config.DELAY
    else:
        raise ValueError(f"Unknown variable: {variable_name}")

def on_button_pressed(app, event: Button.Pressed) -> None:
    """Handle button presses and update values dynamically."""
    button = event.button
    button_name = button.name

    if button_name:
        # Strip everything before the first hyphen, including the hyphen itself
        button_name = button_name.split("-", 1)[-1]  # Get the part after the first hyphen
        
        parts = button_name.split("_")
        if len(parts) == 2:
            variable_name, amount = parts[0], int(parts[1])

            # Update the variable value in config.py
            if hasattr(config, variable_name.upper()):
                current_value = getattr(config, variable_name.upper())
                new_value = current_value + amount
                setattr(config, variable_name.upper(), new_value)

                # Update corresponding Input field
                input_field = app.query_one(f"#{variable_name}_input")
                input_field.value = str(new_value)

                # Update the status box row
                update_status_box(app, variable_name, new_value)

                # Refresh UI to reflect changes
                app.refresh()

def on_save_button_pressed(app, event: Button.Pressed) -> None:
    """Handle the Save button press to save the values."""
    button = event.button
    button_name = button.name

    if button_name:
        variable_name = button_name.replace("save_val-", "")
        variable_name = variable_name.replace("_save", "")  # Extract the variable name from button
        input_field = app.query_one(f"#{variable_name}_input", Input)

        new_value = int(input_field.value)
        setattr(config, variable_name.upper(), new_value)
        
        update_status_box(app, variable_name, new_value)
        app.refresh()

def save_uart_settings(app, event: Button.Pressed) -> None:

    cur_uart_port = str(app.query_one(f"#uart_port_input", Input).value)
    cur_baud_rate = int(app.query_one(f"#baud_rate_input", Input).value)

    config.SERIAL_PORT = cur_uart_port
    config.BAUD_RATE = cur_baud_rate

    main_content = app.query_one(".main_content", Vertical)
    main_content.border_title = f"{config.SERIAL_PORT} {config.BAUD_RATE}"
    app.refresh()

def change_baudrate(new_baudrate):
    """Change the baud rate using the app_instance's serial connection"""
    if app_instance is None:
        add_text("[ERROR] App instance not available")
        return False
    
    if not hasattr(app_instance, 'serial_connection'):
        add_text("[ERROR] No serial connection in app instance")
        return False

    input_field = app_instance.query_one(f"#baud_rate_input")
    input_field.value = str(new_baudrate)
    
    serial_conn = app_instance.serial_connection
    
    if serial_conn is None or not serial_conn.is_open:
        add_text("[ERROR] Serial port not initialized or closed")
        return False
    
    try:
        old_baudrate = serial_conn.baudrate
        serial_conn.baudrate = new_baudrate
        config.BAUD_RATE = new_baudrate

        main_content = app_instance.query_one(".main_content", Vertical)
        if functions.get_config_value("log_time") == 0:
            main_content.border_title = f"{config.SERIAL_PORT} {config.BAUD_RATE}"
        else:
            time = str(functions.get_config_value("log_time"))
            main_content.border_title = f"{config.SERIAL_PORT} {config.BAUD_RATE} \\[{time}.log]"
        
        return True
        
    except ValueError as e:
        add_text(f"[ERROR] Invalid baud rate {new_baudrate}: {e}")
    except serial.SerialException as e:
        add_text(f"[ERROR] Serial error changing baud rate: {e}")
        # Attempt to revert
        try:
            serial_conn.baudrate = old_baudrate
        except:
            add_text("[WARNING] Failed to revert baud rate")
    return False

def update_status_box(app, variable_name, new_value):
    column_keys = list(app.status_box.columns.keys())

    # We only have two columns: "Attribute" and "Value"
    if variable_name == "length":
        row_key = list(app.status_box.rows.keys())[0]  # The first row
        column_key = column_keys[1]  # The Value column for 'length'
    elif variable_name == "repeat":
        row_key = list(app.status_box.rows.keys())[1]  # The first row
        column_key = column_keys[1]  # The Value column for 'repeat'
    elif variable_name == "delay":
        row_key = list(app.status_box.rows.keys())[2]  # The first row
        column_key = column_keys[1]  # The Value column for 'delay'
    elif variable_name == "elapsed":
        row_key = list(app.status_box.rows.keys())[3]  # The first row
        column_key = column_keys[1]  # The Value column for 'delay'

    app.status_box.update_cell(row_key, column_key, str(new_value))

def run_custom_function(app, event):
    """Handle custom function buttons with enhanced logging"""
    button = event.button
    button_name = button.name
    debug = DEBUG_MODE  # Set to False after testing

    log_message(f"[CUSTOM] Button pressed: '{button_name}'")

    if button_name:
        try:
            variable_name = int(button_name.replace("custom_function-", ""))
            log_message(f"[CUSTOM] Condition index: {variable_name}")

            if 0 <= variable_name < len(config.conditions):
                func_name = config.conditions[variable_name][3]
                log_message(f"[CUSTOM] Executing: {func_name}")
                
                # Use the centralized execution function
                success = execute_condition_action(func_name, debug)
                
                if not success:
                    log_message(f"[CUSTOM] Failed to execute {func_name}")
            else:
                log_message(f"[CUSTOM] Invalid index: {variable_name}")

        except ValueError:
            log_message(f"[CUSTOM] Invalid button format: '{button_name}'")
        except Exception as e:
            log_message(f"[CUSTOM] Error: {str(e)}")
            if debug:
                log_message(f"[DEBUG] {traceback.format_exc()}")

def write_to_log(text: str, log_time: int):
    """Write text to a log file named {log_time}.log in the logs directory"""
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create filename using log_time value
    log_file = os.path.join(logs_dir, f"{log_time}.log")
    
    # Append text to log file
    with open(log_file, "a") as f:
        f.write(f"{text}")

def add_text(text):
    """Add text to the log widget and optionally to a log file"""
    if hasattr(functions, 'text_area'):
        functions.text_area.write(text + "\n")
    
    log_time = get_config_value("log_time")
    if log_time > 0:
        write_to_log(text+"\n", log_time)

def update_text(text):
    """Update text without adding newlines"""
    if hasattr(functions, 'text_area'):
        functions.text_area.write(text)

def save_config(app):
    config_file = get_config_value("conFile")
    temp_file = config_file + ".tmp"
    new_file = str(app.query_one(f"#config_file_input", Input).value)
    
    try:
        # Get current values
        serial_port = get_config_value("serial_port")
        baud_rate = get_config_value("baud_rate")
        length = get_config_value("length")
        repeat = get_config_value("repeat")
        delay = get_config_value("delay")
        
        # Get triggers
        triggers = []
        for i in range(8):
            triggers.append([
                get_config_value(f"trigger_{i}_value"),
                get_config_value(f"trigger_{i}_state")
            ])
        
        # Read existing config
        existing_content = ""
        custom_functions = []
        imports = []
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                existing_content = f.read()
            
            # Extract imports and functions
            import_pattern = re.compile(r'^import .+?$|^from .+? import .+?$', re.MULTILINE)
            imports = import_pattern.findall(existing_content)
            
            func_pattern = re.compile(r'^(def \w+\(.*?\):.*?)(?=^(?:def \w+\(|\Z))', re.MULTILINE | re.DOTALL)
            custom_functions = [fn.strip() for fn in func_pattern.findall(existing_content) if fn.strip()]
        
        # Write new config file
        with open(temp_file, 'w') as f:
            # Write imports
            if imports:
                f.write("######\n# LEAVE THESE IMPORTS!\n######\n")
                f.write("\n".join(imports) + "\n\n")
            
            # Write config values
            f.write("######\n# config values\n######\n\n")
            f.write(f"SERIAL_PORT = {repr(serial_port)}\n")
            f.write(f"BAUD_RATE = {baud_rate}\n\n")
            f.write(f"LENGTH = {length}\n")
            f.write(f"REPEAT = {repeat}\n")
            f.write(f"DELAY = {delay}\n\n")
            
            # Write triggers
            f.write("###\n# ^ = pullup, v = pulldown\n###\n")
            f.write("triggers = [\n")
            for i, (value, state) in enumerate(triggers):
                f.write(f"    [{repr(value)}, {state}],  #{i}\n")
            f.write("]\n")
            
            # Write conditions if they exist
            if hasattr(config, 'conditions') and config.conditions:
                f.write("\n###\n# name, enabled, string to match\n###\n")
                f.write("conditions = [\n")
                for condition in config.conditions:
                    f.write(f"    {condition},\n")
                f.write("]\n")
            
            # Write custom functions with proper spacing
            if custom_functions:
                f.write("\n######\n# Custom functions\n######\n")
                f.write("\n\n".join(custom_functions))
                f.write("\n")  # Single newline at end
        
        # Finalize file
        if os.path.exists(new_file):
            os.remove(new_file)
        os.rename(temp_file, new_file)
        config.CONFILE = new_file
        add_text(f"[SAVED] config {new_file} saved")
        
    except Exception as e:
        log_message(f"Error saving config: {str(e)}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise

def start_serial():
    try:
        ser = serial.Serial(
            port=config.SERIAL_PORT,
            baudrate=config.BAUD_RATE,
            timeout=0.1,          # Read timeout (seconds)
            write_timeout=1.0,    # Write timeout
            inter_byte_timeout=0.05, # Between bytes
            exclusive=True,        # Prevent multiple access
            rtscts=False,           # Enable hardware flow control (disable for tigard)
            dsrdtr=False            # Additional flow control (disable for tigard)
        )
        add_text("Connected to serial port.")
        return ser
    except serial.SerialException as e:
        add_text(f"[ERROR] Serial exception: {e}")
        return None

def send_uart_message(message):
    """Send exactly one raw UART character, using the configured newline if set."""
    try:
        conn = getattr(app_instance, "serial_connection", None)
        if not conn or not conn.is_open:
            log_message("[UART] Not sent - UART disconnected")
            return False

        # Skip newline removal if the configuration is blank
        if config.UART_NEWLINE:
            if message.endswith(config.UART_NEWLINE):
                message = message[: -len(config.UART_NEWLINE)]
            # Append exactly one instance of the configured newline
            message += config.UART_NEWLINE

        # Send only the raw character(s)
        raw = message.encode("utf-8")
        conn.write(raw)
        conn.flush()

        log_message(f"[UART] Sent raw: {repr(raw)}")
        return True

    except Exception as e:
        log_message(f"[UART TX ERROR] {e}")
        return False


def read_uart_buffer():
    """Read data into app_instance.serial_buffer and return it."""
    conn = getattr(app_instance, "serial_connection", None)
    if not conn or not conn.is_open:
        log_message("[UART] Read skipped - No connection")
        return app_instance.serial_buffer
    try:
        data = conn.read_all().decode("utf-8", errors="replace")
        if data:
            app_instance.serial_buffer += data
        log_message(f"[UART] Buffer read: {app_instance.serial_buffer.strip()}")
        return app_instance.serial_buffer
    except Exception as e:
        log_message(f"[UART RX ERROR] {e}")
        return app_instance.serial_buffer

def get_conditions_buffer_size(debug=False):
    """Return the maximum length of condition strings with debug option"""
    if not hasattr(config, 'conditions') or not config.conditions:
        if debug:
            log_message("[DEBUG] No conditions defined, using default buffer size 256")
        return 256
    
    valid_lengths = [len(cond[2]) for cond in config.conditions if cond[2]]
    if not valid_lengths:
        if debug:
            log_message("[DEBUG] All condition strings are empty, using default buffer size 256")
        return 256
    
    max_size = max(valid_lengths)
    if debug:
        log_message(f"[DEBUG] Calculated buffer size: {max_size} (from {len(config.conditions)} conditions)")
    return max_size

def check_conditions(self, buffer, debug=False):
    """Check buffer against all conditions by examining every position"""
    #if debug:
        #log_message(f"[DEBUG] Checking buffer ({len(buffer)} chars): {repr(buffer)}")
        
    if not hasattr(config, 'conditions') or not config.conditions:
        if debug:
            log_message("[DEBUG] No conditions to check against")
        return None
        
    for i, condition in enumerate(config.conditions):
        trigger_str = condition[2]
        if not trigger_str:  # Skip empty trigger strings
            continue
            
        trigger_len = len(trigger_str)
        buffer_len = len(buffer)
        
        #if debug:
            #log_message(f"[DEBUG] Checking condition {i} for '{trigger_str}' (length: {trigger_len})")
        
        # Check every possible starting position in the buffer
        for pos in range(buffer_len - trigger_len + 1):
            # Compare slice of buffer with trigger string
            if buffer[pos:pos+trigger_len] == trigger_str:
                try:
                    condition_active = config.conditions[i][1]  # Get state from config
                    
                    if not condition_active:
                        if debug:
                            log_message(f"[DEBUG] Condition {i} matched at position {pos} but switch is OFF")
                        continue
                    
                    if debug:
                        log_message(f"[DEBUG] MATCHED condition {i} at position {pos}: {condition[0]} -> {condition[3]}")
                    return condition[3]
                    
                except Exception as e:
                    if debug:
                        log_message(f"[DEBUG] Condition check failed for {i}: {str(e)}")
                    continue
    
    #if debug:
        #log_message("[DEBUG] No conditions matched")
    return None

def execute_condition_action(action_name, debug=False):
    """Execute the named action function using run_custom_function logic"""
    if debug:
        log_message(f"[ACTION] Attempting to execute: {action_name}")
    
    try:
        # Check if action exists in config module
        module_name = 'config'
        module = importlib.import_module(module_name)
        
        if hasattr(module, action_name):
            if debug:
                log_message(f"[ACTION] Found {action_name} in {module_name}")
            getattr(module, action_name)()
            return True
        
        # Check if action exists in functions module
        if hasattr(sys.modules[__name__], action_name):
            if debug:
                log_message(f"[ACTION] Found {action_name} in functions")
            getattr(sys.modules[__name__], action_name)()
            return True
        
        # Check if action exists in globals
        if action_name in globals():
            if debug:
                log_message(f"[ACTION] Found {action_name} in globals")
            globals()[action_name]()
            return True
        
        log_message(f"[ACTION] Function '{action_name}' not found in any module")
        return False
        
    except Exception as e:
        log_message(f"[ACTION] Error executing {action_name}: {str(e)}")
        if debug:
            log_message(f"[DEBUG] Full exception: {traceback.format_exc()}")
        return False

def get_glitch_elapsed():
    gtime = get_config_value("glitch_time")
    if gtime <= 0:
        return "000:00:00"
    # Assuming gtime contains the start timestamp
    elapsed = int(time.time() - gtime)
    return f"{elapsed//3600:03d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}"

def start_glitch(glitch_len, trigger_repeats, delay):
    s.glitch.repeat = glitch_len
    s.glitch.ext_offset = delay
    #add_text(f"[GLITCHING]: length:{glitch_len}, offset:{delay}, repeat:{trigger_repeats}")
            
    triggers = [] # Get triggers
    triggers_set = False
    for i in range(8):
        triggers.append([
            get_config_value(f"trigger_{i}_value"),
            get_config_value(f"trigger_{i}_state")
        ])
    for i, (value, state) in enumerate(triggers):
        if state is True:
            triggers_set = True
            if value == "^":
                #add_text(f"[GLITCHING]: armed: {i} ^")
                s.arm(i, Scope.RISING_EDGE)
            elif value == "v":
                #add_text(f"[GLITCHING]: armed: {i} v")
                s.arm(i, Scope.FALLING_EDGE)

    if triggers_set is False:
        #add_text(f"[GLITCHING]: repeat:{trigger_repeats}")
        for _ in range(trigger_repeats):
            s.trigger()

def launch_glitch():
    length = functions.get_config_value("length")
    repeat = functions.get_config_value("repeat")
    delay = functions.get_config_value("delay")
    start_glitch(length, repeat, delay)

async def glitch(self):
    functions.log_message("[GLITCHING] Starting glitch monitor")
    previous_gtime = None  # Track the previous state
    
    while True:
        try:
            gtime = get_config_value("glitch_time")
            elapsed_time = get_glitch_elapsed()
            functions.update_status_box(self, "elapsed", elapsed_time)
            
            # Only update if the state has changed
            #if gtime != previous_gtime:
            if gtime > 0:
                self.status_box.border_subtitle = "running"
                self.status_box.styles.border_subtitle_color = "#5E99AE"
                self.status_box.styles.border_subtitle_style = "bold"

                length = functions.get_config_value("length")
                repeat = functions.get_config_value("repeat")
                delay = functions.get_config_value("delay")
                start_glitch(length, repeat, delay)
            else:
                self.status_box.border_subtitle = "stopped"
                self.status_box.styles.border_subtitle_color = "#B13840"
                self.status_box.styles.border_subtitle_style = "none"
                
                #previous_gtime = gtime  # Update the previous state

        except Exception as e:
            print(f"Update error: {e}")
        
        await asyncio.sleep(0.1)

def glitching_switch(value):
    switch = app_instance.query_one("#glitch-switch", Switch)  
    switch.value = value  # Force turn off

def run_output_high(gpio, time):
    s.io.add(gpio, 1, delay=time)
    s.io.upload()
    s.trigger()

def run_output_low(gpio, time):
    s.io.add(gpio, 0, delay=time)
    s.io.upload()
    s.trigger()

async def monitor_buffer(self):
    """Background task to monitor serial buffer for conditions"""
    debug = True
    buffer_size = functions.get_conditions_buffer_size(debug)
    
    functions.log_message("[CONDITIONS] Starting monitor")
    
    while self.run_serial:
        if not getattr(self, '_serial_connected', False):
            await asyncio.sleep(1)
            continue
            
        async with self.buffer_lock:
            current_buffer = self.serial_buffer
            max_keep = buffer_size * 3  # Keep enough buffer to catch split matches
            
            if len(current_buffer) > max_keep:
                # Keep last max_keep characters, but ensure we don't cut a potential match
                keep_from = len(current_buffer) - max_keep
                # Find the last newline before this position to avoid breaking lines
                safe_cut = current_buffer.rfind('\n', 0, keep_from)
                if safe_cut != -1:
                    keep_from = safe_cut + 1
                self.serial_buffer = current_buffer[keep_from:]
                current_buffer = self.serial_buffer
                if debug:
                    log_message(f"[DEBUG] Truncated buffer from {len(current_buffer)+keep_from} to {len(current_buffer)} chars")
        
        if current_buffer:
            action = functions.check_conditions(self, current_buffer, debug)
            if action:
                functions.log_message(f"[CONDITIONS] Triggering: {action}")
                success = functions.execute_condition_action(action, debug)
                
                if success:
                    async with self.buffer_lock:
                        # Clear the buffer after successful match
                        self.serial_buffer = ""
                else:
                    functions.log_message("[CONDITIONS] Action failed")
        
        await asyncio.sleep(0.1)

def clear_text():
    text_area.clear()

def end_program():
    exit()

##################
# Faultycat stuff
##################

def faulty_connect(comport: str = DEFAULT_FAULTY_COMPORT) -> bool:
    try:
        faulty_worker.set_serial_port(comport)
        if not faulty_worker.validate_serial_connection():
            #if debug:
                #log_message(f"Connection failed on {comport}")
            return False
        faulty_worker.board_uart.open()
        time.sleep(0.1)
        #if debug:
            #log_message("Board connected")
        return True
    except Exception as e:
        #if debug:
            #log_message(f"Connection error: {e}")
        return False

def faulty_arm() -> bool:
    try:
        uart, cmd = faulty_worker.board_uart, faulty_worker.board_configurator.board_commands
        uart.send(cmd.COMMAND_DISARM.value.encode("utf-8"))
        time.sleep(1)
        uart.send(cmd.COMMAND_ARM.value.encode("utf-8"))
        #if debug:
            #log_message("Board armed")
        return True
    except Exception as e:
        #if debug:
            #log_message(f"Arm error: {e}")
        return False

def faulty_send_pulse() -> bool:
    try:
        faulty_worker.board_uart.send(
            faulty_worker.board_configurator.board_commands.COMMAND_PULSE.value.encode("utf-8")
        )
        #if debug:
            #log_message("Pulse sent")
        return True
    except Exception as e:
        #if debug:
            #log_message(f"Pulse error: {e}")
        return False

def faulty_disarm(close_uart: bool = True) -> bool:
    try:
        uart, cmd = faulty_worker.board_uart, faulty_worker.board_configurator.board_commands
        uart.send(cmd.COMMAND_DISARM.value.encode("utf-8"))
        if close_uart:
            uart.close()
        #if debug:
            #log_message("Board disarmed")
        return True
    except Exception as e:
        #if debug:
            #log_message(f"Disarm error: {e}")
        return False