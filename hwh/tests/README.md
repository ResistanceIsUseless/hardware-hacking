# hwh Tests

Test suite for the hardware hacking toolkit.

## Structure

- `test_buspirate.py` - Bus Pirate backend tests

## Running Tests

### Basic Test Run

From the parent directory (hardware-hacking):

```bash
cd hardware-hacking
PYTHONPATH=. python3 hwh/tests/test_buspirate.py
```

### With pytest (when available)

```bash
cd hardware-hacking
pytest hwh/tests/
```

## Test Requirements

Tests require actual hardware connected:

- **test_buspirate.py**: Requires Bus Pirate v5/v6 connected
- May require specific wiring or target devices

## Adding Tests

When adding tests:

1. Name test files `test_*.py`
2. Include hardware requirements in docstring
3. Add to this README
4. Consider whether hardware is required or can be mocked

## Hardware-Specific Tests

Many tests require real hardware. To run a specific device test:

```bash
# Check device is connected first
python3 -c "from hwh.detect import detect; print(detect())"

# Run test if device present
python3 hwh/tests/test_buspirate.py
```

## Future Work

- Add unit tests for components that don't require hardware
- Mock hardware backends for CI/CD testing
- Integration tests for multi-device workflows
- Performance benchmarks
