#!/bin/bash
#
# hwh Setup Script
#
# Installs the hwh toolkit and all dependencies
#

set -e  # Exit on error

echo "========================================"
echo "  hwh - Hardware Hacking Toolkit Setup"
echo "========================================"
echo

# Check Python version
echo "Checking Python version..."
python3 --version

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python 3.10 or higher required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"
echo

# Check we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from hwh/ directory"
    echo "Usage: cd hwh && ./setup.sh"
    exit 1
fi

# Install package
echo "Installing hwh package..."
pip3 install -e .

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install hwh package"
    exit 1
fi

echo "✓ hwh package installed"
echo

# Install optional dependencies
echo "Installing optional dependencies..."
pip3 install cobs flatbuffers textual

if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Some optional dependencies failed to install"
    echo "   The toolkit will still work, but some features may be limited"
else
    echo "✓ Optional dependencies installed"
fi

echo

# Verify installation
echo "Verifying installation..."
python3 -c "from hwh import detect; print('✓ hwh module imports successfully')"

if [ $? -ne 0 ]; then
    echo "❌ Error: hwh module failed to import"
    exit 1
fi

# Check for connected devices
echo
echo "Scanning for connected devices..."
python3 -c "
from hwh.detect import detect
devices = detect(identify_unknown=True)
if devices:
    print(f'✓ Found {len(devices)} device(s):')
    for dev_id, info in devices.items():
        print(f'    - {dev_id}: {info.device_type} ({info.port})')
else:
    print('  No devices found (connect hardware and try again)')
"

echo
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo
echo "Next steps:"
echo "  1. Test device detection:"
echo "     cd .. && python3 hwh/examples/01_device_discovery.py"
echo
echo "  2. Read the documentation:"
echo "     cat README.md"
echo
echo "  3. Try UART automation (if you have a target):"
echo "     cd .. && python3 hwh/examples/02_uart_auto_interact.py"
echo
echo "  4. See examples/README.md for more examples"
echo
