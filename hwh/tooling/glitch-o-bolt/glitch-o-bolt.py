#!/usr/bin/env python3
#
# glitch-o-matic 2.0 - Optimized Version
# Enhanced serial data performance while maintaining all existing features
#
# requirements: textual
import os
import sys
import time
import types
import argparse
import importlib.util
import concurrent.futures

import asyncio
import select
import serial
import functools

from scope import Scope
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, DataTable, Input, Button, Switch, Log
from textual.messages import Message

# Define specific names for each control row
control_names = ["length", "repeat", "delay"]

def load_config(path):
    spec = importlib.util.spec_from_file_location("dynamic_config", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Inject the loaded config as 'config'
    sys.modules['config'] = module

class PersistentInput(Input):
    PREFIX = "$> "  # The permanent prefix

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value = self.PREFIX  # Set initial value

    def on_input_changed(self, event: Input.Changed) -> None:
        """Ensure the prefix is always present."""
        if not event.value.startswith(self.PREFIX):
            self.value = self.PREFIX  # Restore the prefix
        elif len(event.value) < len(self.PREFIX):
            self.value = self.PREFIX  # Prevent deleting

def set_app_instance(app):
    functions.app_instance = app

class SerialDataMessage(Message):
    def __init__(self, data: str):
        super().__init__()  # Call the parent class constructor
        self.data = data  # Store the serial data

class LayoutApp(App):
    CSS_PATH = "style.tcss"

    async def on_ready(self) -> None:
        #set_app_instance(self)
        self.run_serial = True
        self.serial_buffer = ""  # Add buffer storage
        self.buffer_lock = asyncio.Lock()  # Add thread-safe lock
        try:
            functions.s = Scope()
        except IOError:
            s = None
            print("Warning: Scope not connected, running in simulation mode")
        
        # Start both serial tasks
        asyncio.create_task(self.connect_serial())
        asyncio.create_task(functions.monitor_buffer(self))
        asyncio.create_task(functions.glitch(self))
        functions.log_message("[DEBUG] Serial tasks created")

    async def connect_serial(self):
        """Stable serial connection with proper error handling"""
        switch_uart = self.query_one("#uart_switch")
        
        while self.run_serial:
            if switch_uart.value:
                if not getattr(self, '_serial_connected', False):
                    try:
                        # Close existing connection if any
                        if hasattr(self, 'serial_connection') and self.serial_connection:
                            self.serial_connection.close()
                        
                        # Establish new connection
                        self.serial_connection = functions.start_serial()
                        if self.serial_connection and self.serial_connection.is_open:
                            # Configure for reliable operation
                            self.serial_connection.timeout = 0.5
                            self.serial_connection.write_timeout = 1.0
                            self._serial_connected = True
                            functions.log_message("[SERIAL] Connected successfully")
                            asyncio.create_task(self.read_serial_loop())
                        else:
                            raise serial.SerialException("Connection failed")
                    except Exception as e:
                        self._serial_connected = False
                        functions.log_message(f"[SERIAL] Connection error: {str(e)}")
                        switch_uart.value = False
                        await asyncio.sleep(2)  # Wait before retrying
            else:
                if getattr(self, '_serial_connected', False):
                    if hasattr(self, 'serial_connection') and self.serial_connection:
                        self.serial_connection.close()
                    self._serial_connected = False
                    functions.log_message("[SERIAL] Disconnected")
            
            await asyncio.sleep(1)  # Check connection status periodically

    async def read_serial_loop(self):
        """Serial reading that perfectly preserves original line endings"""
        buffer = ""
        
        while self.run_serial and getattr(self, '_serial_connected', False):
            try:
                # Read available data (minimum 1 byte)
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.serial_connection.read(max(1, self.serial_connection.in_waiting))
                )
                
                if data:
                    decoded = data.decode('utf-8', errors='ignore')
                    
                    # Store raw data in condition monitoring buffer
                    async with self.buffer_lock:
                        self.serial_buffer += decoded
                    
                    # Original character processing
                    for char in decoded:
                        if char == '\r':
                            continue
                        
                        buffer += char
                        
                        if char == '\n':
                            self.post_message(SerialDataMessage(buffer))
                            buffer = ""
                    
                    if buffer:
                        self.post_message(SerialDataMessage(buffer))
                        buffer = ""
                
                await asyncio.sleep(0.01)
                
            except serial.SerialException as e:
                functions.log_message(f"[SERIAL] Read error: {str(e)}")
                self._serial_connected = False
                break
            except Exception as e:
                functions.log_message(f"[SERIAL] Unexpected error: {str(e)}")
                await asyncio.sleep(0.1)

    async def monitor_conditions(self):
        """Background task to monitor serial buffer for conditions with debug"""
        debug = functions.DEBUG_MODE  # Set to False to disable debug logging after testing
        buffer_size = functions.get_conditions_buffer_size(debug)
        
        if debug:
            functions.log_message("[DEBUG] Starting condition monitor")
            functions.log_message(f"[DEBUG] Initial buffer size: {buffer_size}")
            functions.log_message(f"[DEBUG] Current conditions: {config.conditions}")
        
        while self.run_serial:
            if hasattr(self, '_serial_connected') and self._serial_connected:
                # Get a snapshot of the buffer contents
                async with self.buffer_lock:
                    current_buffer = self.serial_buffer
                    if debug and current_buffer:
                        functions.log_message(f"[DEBUG] Current buffer length: {len(current_buffer)}")
                    
                    # Keep reasonable buffer size
                    if len(current_buffer) > buffer_size * 2:
                        self.serial_buffer = current_buffer = current_buffer[-buffer_size*2:]
                        if debug:
                            functions.log_message(f"[DEBUG] Trimmed buffer to {len(current_buffer)} chars")
                
                # Check for conditions
                action = functions.check_conditions(self, current_buffer, debug)
                if action:
                    if debug:
                        functions.log_message(f"[DEBUG] Executing action: {action}")
                    functions.execute_condition_action(action, debug)
                elif debug and current_buffer:
                    functions.log_message("[DEBUG] No action triggered")
        
        await asyncio.sleep(0.1)  # Check 10 times per secon

    async def on_key(self, event: events.Key) -> None:
        """Handles input with proper newline preservation."""
        # Prevent Textual default handling immediately
        if event.key == "enter":
            event.prevent_default()

            if self.input_field.has_focus:
                text_to_send = self.input_field.value

                # Skip empty input
                if not text_to_send:
                    return

                serial_connection = getattr(self, "serial_connection", None)
                if serial_connection and serial_connection.is_open:
                    try:
                        # Send exactly once via executor
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: functions.send_uart_message(text_to_send)
                        )

                        # Echo to console once
                        display_text = f"> {text_to_send.rstrip()}"
                        functions.add_text(display_text)

                    except Exception as e:
                        functions.log_message(f"[UART TX ERROR] {str(e)}")
                        functions.add_text(">> Failed to send")
                else:
                    functions.add_text(">> Not sent - UART disconnected")

                # Clear after handling
                self.input_field.value = ""

    async def on_serial_data_message(self, message: SerialDataMessage) -> None:
        """Display serial data exactly as received"""
        if hasattr(functions, 'text_area'):
            # Write the data exactly as it should appear
            if functions.get_config_value("uart_output_enabled") is True:
                functions.text_area.write(message.data)

            log_time = functions.get_config_value("log_time")
            if log_time > 0:
                functions.write_to_log(message.data, log_time)
            #functions.add_text(message.data)
            functions.text_area.scroll_end()

    def read_from_serial_sync(self):
        """Synchronous line reading with proper timeout handling"""
        if not self.serial_connection:
            return b""
        
        try:
            # Read with timeout
            ready, _, _ = select.select([self.serial_connection], [], [], 0.01)
            if ready:
                # Read until newline or buffer limit
                return self.serial_connection.read_until(b'\n', size=4096)
            return b""
        except Exception as e:
            functions.log_message(f"[ERROR] Serial read error: {str(e)}")
            return b""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id_parts = event.button.name
        parts = button_id_parts.split("-")
        button_id = parts[0]
        if(button_id == "exit_button"):
            functions.end_program() 
        if(button_id == "clear_button"):
            functions.clear_text()
        if(button_id == "btn_glitch"):
            functions.launch_glitch()
        if(button_id == "save_config"):
            functions.save_config(self)
        if(button_id == "toggle_trigger"):
            functions.toggle_trigger(self, int(parts[1])) 
        if(button_id == "change_val"):
            functions.on_button_pressed(self, event)
        if(button_id == "save_val"):
            functions.on_save_button_pressed(self, event) 
        if(button_id == "custom_function"):
            functions.run_custom_function(self, event) 
        if(button_id == "save_uart"):
            functions.save_uart_settings(self, event) 

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch toggle events"""
        switch = event.switch
        
        # Only handle switches with our specific class
        if "trigger-switch" in switch.classes:
            try:
                # Extract index from switch ID
                index = int(switch.id.split("_")[-1])
                new_state = bool(event.value)  # Ensure boolean
                config.triggers[index][1] = new_state  # Update config
                functions.set_triggers()                  
            except (ValueError, IndexError, AttributeError) as e:
                if functions.DEBUG_MODE:
                    functions.log_message(f"[ERROR] Failed to process trigger switch: {str(e)}")

        if "condition-switch" in switch.classes:
            try:
                # Extract index from switch ID
                index = int(switch.id.split("_")[-1])
                new_state = bool(event.value)  # Ensure boolean
                
                # Update config
                config.conditions[index][1] = new_state
                
                if functions.DEBUG_MODE:
                    functions.log_message(f"[CONDITION] Updated switch {index} to {new_state}")
                    functions.log_message(f"[CONDITION] Current states: {[cond[1] for cond in config.conditions]}")
                    
            except (ValueError, IndexError, AttributeError) as e:
                if functions.DEBUG_MODE:
                    functions.log_message(f"[ERROR] Failed to process condition switch: {str(e)}")

        if "logging-switch" in switch.classes:
            if functions.DEBUG_MODE:
                curr_time = functions.get_config_value("log_time")
                functions.log_message(f"[FUNCTION] logging toggled: {curr_time}")
            
            if bool(event.value) is True:
                functions.set_log_time(int(time.time()))  # Uses the 'time' module
            else:
                functions.set_log_time(0)
            
            main_content = self.query_one("#main_content")
            log_time = functions.get_config_value("log_time")  # Renamed to avoid conflict
            port = str(functions.get_config_value("serial_port"))
            baud = str(functions.get_config_value("baud_rate"))

            if log_time == 0:  # Now using 'log_time' instead of 'time'
                main_content.border_title = f"{port} {baud}"
            else:
                main_content.border_title = f"{port} {baud} \\[{log_time}.log]"

        if "uart-output-switch" in switch.classes:
            if bool(event.value) is True:
                functions.set_config_value("uart_output_enabled", True)
            else:
                functions.set_config_value("uart_output_enabled", False)
            functions.log_message(f"[FUNCTION] uart output toggled: {event.value}")



        if "glitch-switch" in switch.classes:
            if functions.DEBUG_MODE:
                curr_time = functions.get_config_value("glitch_time")
                functions.log_message(f"[FUNCTION] glitching toggled: {curr_time}")
            
            if bool(event.value) is True:
                functions.set_glitch_time(int(time.time()))  # Uses the 'time' module
            else:
                functions.set_glitch_time(0)

    def compose(self) -> ComposeResult:
        with Vertical(classes="top_section"):
            # Use Vertical here instead of Horizontal
            with Vertical(classes="top_left"):
                
                # UART Box - appears second (below)
                with Vertical(classes="uart_box") as uart_box:
                    uart_box.border_title = "uart settings"

                    with Horizontal(classes="onerow"):
                        yield Static("port:", classes="uart_label")
                        yield Input(
                            classes="control_input",
                            id="uart_port_input",
                            name="uart_port_input",
                            value=str(functions.get_config_value("serial_port"))
                        )

                    with Horizontal(classes="onerow"):
                        yield Static("baud:", classes="uart_label")
                        yield Input(
                            classes="control_input",
                            id="baud_rate_input",
                            name="baud_rate_input",
                            value=str(functions.get_config_value("baud_rate"))
                        )
                        yield Button("save", classes="btn_save", id="save_uart", name="save_uart")

                # Config Box - appears first (on top)
                with Vertical(classes="config_box") as config_box:
                    config_box.border_title = "config"

                    with Horizontal(classes="onerow"):
                        yield Static("file:", classes="uart_label")
                        yield Input(
                            classes="control_input",
                            id="config_file_input",
                            name="config_file_input",
                            value=str(functions.get_config_value("conFile"))
                        )
                    with Horizontal(classes="onerow"):
                        yield Button("save", classes="btn_save", id="save_config", name="save_config")

            yield Static("glitch-o-bolt v2.0", classes="program_name")
            yield Static(" ")  # Show blank space
            
            for name in control_names:
                with Horizontal(classes="control_row"):
                    yield Static(f"{name}:", classes="control_label")
                    for amount in [-100, -10, -1]:
                        yield Button(str(amount), classes=f"btn btn{amount}", name=f"change_val-{name}_{amount}")

                    yield Input(
                        classes="control_input",
                        value=str(functions.get_config_value(name)),  
                        type="integer",
                        id=f"{name}_input"  # Use `id` instead of `name`
                    )
                    yield Button("save", classes="btn_save", name=f"save_val-{name}_save")

                    for amount in [1, 10, 100]:
                        yield Button(f"+{amount}", classes=f"btn btn-{amount}",  name=f"change_val-{name}_{amount}")

            with Horizontal(classes="top_right"):
                with Vertical(classes="switch_box") as switch_box:
                    #yield Static("glitch", classes="switch_title")
                    yield Button("glitch", classes="btn_glitch", name=f"btn_glitch")
                    yield Switch(classes="glitch-switch", id="glitch-switch", animate=False)

                # Create and store DataTable for later updates
                self.status_box = DataTable(classes="top_box", name="status_box")
                self.status_box.border_title = "status"
                self.status_box.border_subtitle = "stopped"
                self.status_box.styles.border_subtitle_color = "#B13840"
                self.status_box.show_header = False
                self.status_box.show_cursor = False

                self.status_box.add_columns("Attribute", "Value")

                # Add rows for config values
                self.status_box.add_row(" length: ", str(functions.get_config_value("length")), key="row1")
                self.status_box.add_row(" repeat: ", str(functions.get_config_value("repeat")), key="row2")
                self.status_box.add_row("  delay: ", str(functions.get_config_value("delay")), key="row3")
                self.status_box.add_row("elapsed: ", str(functions.get_glitch_elapsed()), key="row4")

                yield self.status_box  # Yield the stored DataTable
        
        with Horizontal(classes="main_section"):
            with Vertical(classes="left_sidebar"):
                sidebar_content = Vertical(classes="sidebar_triggers_content")
                sidebar_content.border_title = "triggers"
                
                with sidebar_content:
                    with Grid(classes="sidebar_triggers"):                  
                        # Add rows with switches
                        functions.ensure_triggers_exist()
                        for i in range(8):
                            yield Static(f"{i} -")
                            yield Static(f"{functions.get_trigger_string(i)}", id=f"trigger_symbol_{i}", classes="sidebar_trigger_string")
                            yield Switch(
                                classes="trigger-switch sidebar_trigger_switch",
                                value=functions.get_trigger_value(i),
                                animate=False,
                                id=f"trigger_switch_{i}"
                            )
                            yield Button("^v-", classes="btn_toggle_1", name=f"toggle_trigger-{i}")

                
                if hasattr(config, "conditions") and config.conditions:
                    sidebar_content2 = Vertical(classes="sidebar_conditions_content")
                    sidebar_content2.border_title = "conditions"
                    sidebar_content2.styles.height = len(config.conditions) + 1

                    with sidebar_content2:
                        with Grid(classes="sidebar_conditions"):
                            for i in range(len(config.conditions)):
                                yield Static(f"{functions.get_condition_string(i)[:5]} ")
                                
                                if config.conditions[i][2] != "":
                                    yield Switch(
                                        id=f"condition_switch_{i}",
                                        classes="condition-switch sidebar_trigger_switch",  # Added specific class
                                        value=functions.get_condition_value(i),
                                        animate=False
                                    )
                                else:
                                    yield Static(" ")
                                    
                                yield Button("run", classes="btn_toggle_1", name=f"custom_function-{i}")
                sidebar_content3 = Vertical(classes="sidebar_settings_content")
                sidebar_content3.border_title = "misc"
                with sidebar_content3:
                    with Grid(classes="sidebar_settings_switches"):                  
                        # Add rows with switches
                        yield Static(f"uart enable")
                        yield Switch(classes="sidebar_trigger_switch", value=False, animate=False, id="uart_switch")

                        yield Static(f"uart output")
                        yield Switch(classes="uart-output-switch sidebar_trigger_switch", value=False, animate=False)

                        yield Static(f"logging")
                        yield Switch(classes="logging-switch sidebar_trigger_switch", value=False, animate=False)

                    # Centre the exit button
                    with Vertical(classes="centre_settings_buttons"):
                        yield Button("clear main", classes="btn_settings", name="clear_button")
                    with Vertical(classes="centre_settings_buttons"):    
                        yield Button("exit", classes="btn_settings", name="exit_button")


            global text_area  # Use global reference
            with Vertical(id="main_content", classes="main_content") as main_content:
                port = str(functions.get_config_value("serial_port"))
                baud = str(functions.get_config_value("baud_rate"))

                if functions.get_config_value("log_time") == 0:
                    main_content.border_title = f"{port} {baud}"
                else:
                    time = str(functions.get_config_value("log_time"))
                    main_content.border_title = f"{port} {baud} \\[{time}.log]"

                # Use Log() widget instead of TextArea for scrollable content
                functions.text_area = Log(classes="scrollable_log")
                yield functions.text_area  # Make it accessible later
                
                with Horizontal(classes="input_container") as input_row:
                    yield Static("$> ", classes="input_prompt")
                    self.input_field = Input(classes="input_area", placeholder="send to uart", id="command_input" )  # Store reference
                    yield self.input_field

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.py", help="Path to config file")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Config file '{args.config}' not found. Creating an empty one...")
        with open(args.config, "w") as f:
            pass  # Creates a blank file

    load_config(args.config)
    import config
    import functions
    config.CONFILE = args.config
    functions.set_config(config)

    app = LayoutApp()
    set_app_instance(app)  # Pass the app instance to config
    app.run()