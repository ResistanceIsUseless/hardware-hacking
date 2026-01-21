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

# Check if we need a virtual environment (PEP 668)
echo "Checking Python environment..."

# Check if already in a virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✓ Running in virtual environment: $VIRTUAL_ENV"
    PIP_FLAGS=""
elif python3 -m pip install --help | grep -q "break-system-packages"; then
    echo "⚠️  System Python is externally managed (PEP 668)"
    echo ""
    echo "You have two options:"
    echo "  1. Create a virtual environment (recommended)"
    echo "  2. Install with --user flag"
    echo ""
    read -p "Create virtual environment in ../venv? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Creating virtual environment..."
        python3 -m venv ../venv
        echo "✓ Virtual environment created at ../venv"
        echo ""
        echo "To activate the virtual environment:"
        echo "  source ../venv/bin/activate"
        echo ""
        echo "Then re-run this setup script:"
        echo "  ./setup.sh"
        echo ""
        exit 0
    else
        echo "Installing with --user flag..."
        PIP_FLAGS="--user"
    fi
else
    PIP_FLAGS=""
fi

# Install package
echo "Installing hwh package..."
pip3 install $PIP_FLAGS -e .

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install hwh package"
    exit 1
fi

echo "✓ hwh package installed"
echo

# Install optional dependencies
echo "Installing optional dependencies..."
pip3 install $PIP_FLAGS cobs flatbuffers textual

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
echo "     cd .. && python -m hwh detect"
echo
echo "  2. Try the examples:"
echo "     cd .. && python hwh/examples/01_device_discovery.py"
echo
echo "  3. Launch the TUI:"
echo "     cd .. && python -m hwh tui"
echo
echo "  4. Read the documentation:"
echo "     cat README.md"
echo
echo "  5. See examples/README.md for more examples"
echo
