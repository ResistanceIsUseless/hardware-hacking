#!/usr/bin/env python3
"""
Interactive CTF Device Communication

Connects to the CTF device on /dev/cu.usbserial-110 and allows
real-time interaction with the challenge.
"""

import sys
import serial
import threading
import time


class CTFDevice:
    """Interface for CTF challenge device"""

    def __init__(self, port='/dev/cu.usbserial-110', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.monitor_thread = None

    def connect(self):
        """Connect to device"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"[+] Connected to CTF device on {self.port}")
            return True
        except Exception as e:
            print(f"[!] Failed to connect: {e}")
            return False

    def start_monitor(self):
        """Start background monitoring of received data"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def _monitor(self):
        """Background thread to monitor incoming data"""
        print("[*] Monitoring started. Press Ctrl+C to stop.\n")

        while self.running:
            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting)

                # Try to decode as ASCII
                try:
                    text = data.decode('ascii', errors='replace')
                    print(f"\n[RX] {text}", end='')
                except:
                    print(f"\n[RX HEX] {data.hex()}")

            time.sleep(0.05)

    def send(self, data):
        """Send data to device"""
        if isinstance(data, str):
            data = data.encode('ascii')

        self.ser.write(data)
        print(f"[TX] {data}")

    def disconnect(self):
        """Disconnect from device"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        if self.ser:
            self.ser.close()
        print("\n[*] Disconnected")


def interactive_mode():
    """Interactive mode for CTF device"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  CTF Device Interactive Mode                                        ║
║                                                                      ║
║  Connected to: /dev/cu.usbserial-110                                ║
║  Challenge: "Hold one of the 4 challenge buttons to start them"    ║
║                                                                      ║
║  Commands:                                                           ║
║    Type text and press Enter to send                                ║
║    Ctrl+C to exit                                                    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    device = CTFDevice()

    if not device.connect():
        return 1

    device.start_monitor()

    # Send initial reset to see current state
    time.sleep(0.5)
    device.send("\r\n")

    try:
        while True:
            try:
                user_input = input()
                if user_input:
                    device.send(user_input + "\r\n")
            except EOFError:
                break

    except KeyboardInterrupt:
        print("\n[*] Interrupted by user")

    device.disconnect()
    return 0


def auto_probe():
    """Automatically probe the device with common commands"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  CTF Device Auto-Probe                                              ║
║  Trying common commands to explore the device                       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    device = CTFDevice()

    if not device.connect():
        return 1

    device.start_monitor()

    # Wait for any initial messages
    print("[*] Waiting for initial messages...")
    time.sleep(2)

    # Try common commands
    commands = [
        ("Reset", "\r\n"),
        ("Help", "help\r\n"),
        ("Help Alt", "?\r\n"),
        ("Status", "status\r\n"),
        ("Info", "info\r\n"),
        ("Menu", "menu\r\n"),
        ("List", "ls\r\n"),
        ("Button 1", "1\r\n"),
        ("Button 2", "2\r\n"),
        ("Button 3", "3\r\n"),
        ("Button 4", "4\r\n"),
        ("Start", "start\r\n"),
        ("Begin", "begin\r\n"),
    ]

    print("\n[*] Trying common commands...\n")

    for name, cmd in commands:
        print(f"[*] Trying: {name} ({repr(cmd)})")
        device.send(cmd)
        time.sleep(1)

    print("\n[*] Probe complete. Waiting for final messages...")
    time.sleep(2)

    device.disconnect()
    return 0


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == 'probe':
        return auto_probe()
    else:
        return interactive_mode()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
