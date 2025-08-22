# One-Way Clutch Tester

A professional Python application for testing sprag clutches (one-way clutches) used in bicycle hub BLDC motors. This tool provides automated testing cycles with real-time monitoring, fault detection, and automatic recovery systems.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Understanding Test Results](#understanding-test-results)
- [Technical Details](#technical-details)
- [Development](#development)
- [Support](#support)

## Features

### Core Testing Capabilities
- **Automated Clutch Testing**: Configurable forward/reverse torque cycles
- **One-Way Clutch Validation**: Detects clutch wear and failure conditions
- **Real-Time Monitoring**: Live motor parameters, temperature, and current readings
- **Continuous or Fixed Cycle Testing**: Run indefinitely or for specific cycle counts

### Smart Automation
- **Auto COM Port Detection**: Automatically finds and connects to motor controllers
- **Cross-Platform Support**: Works on Windows, Linux, and Raspberry Pi
- **Intelligent Fault Recovery**: Multi-stage automatic fault clearing system
- **Desktop Integration**: One-click execution via desktop shortcut

### Safety & Monitoring
- **Comprehensive Fault Detection**: Real-time monitoring of 32 different fault conditions
- **Temperature Protection**: Monitors motor and controller temperatures
- **Current Limiting**: Configurable motor and battery current limits
- **Visual Status Indicators**: Traffic light system for system status

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/OneWayClutchTester.git
cd OneWayClutchTester
```

### 2. One-Command Setup

**If Python is properly installed**:
```bash
python install.py
```

**If you get "Python was not found" error**:
```bash
py install.py
```

**If both fail, install Python first**:
- **Windows**: Get Python from [Microsoft Store](ms-windows-store://pdp/?ProductId=9NRWMJP3717K) or [python.org](https://www.python.org/downloads/)
- **Linux**: `sudo apt install python3 python3-pip python3-venv`

This single command will:
- Create a virtual environment
- Install all required dependencies
- Create desktop shortcut
- Setup system permissions
- Generate launcher scripts

### 3. Launch Application
**Option A**: Double-click the desktop shortcut "One-Way Clutch Tester"

**Option B**: Use the launcher script:
- **Windows**: Double-click `OneWayClutchTester.bat`
- **Linux**: Double-click `OneWayClutchTester.sh` or run `./OneWayClutchTester.sh`

## System Requirements

### Hardware Requirements
- **Motor Controller**: Modbus RTU compatible motor controller
- **Connection**: Serial/USB cable to motor controller
- **Computer**: Any Windows PC or Linux system (including Raspberry Pi)
- **Memory**: Minimum 512MB RAM
- **Storage**: 100MB free space

### Software Requirements
- **Python**: Version 3.7 or higher (automatically checked during install)
- **Operating System**: 
  - Windows 10 or newer
  - Linux (Ubuntu 18.04+, Raspberry Pi OS, etc.)

### Supported Motor Controllers
- Controllers supporting Modbus RTU protocol
- Baudrate: 115200 (configurable)
- Slave address: 1 (configurable)

## Installation

### Automatic Installation (Recommended)

1. **Download the project**:
   ```bash
   git clone https://github.com/yourusername/OneWayClutchTester.git
   cd OneWayClutchTester
   ```

2. **Run the installer**:
   ```bash
   python install.py
   ```

3. **Follow the setup prompts** - the installer will:
   - Check system compatibility
   - Create virtual environment
   - Install all dependencies
   - Create desktop shortcut
   - Setup permissions (Linux only)

### Manual Installation (Advanced Users)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python src/gui.py
```

## Usage Guide

### First Time Setup

1. **Connect Hardware**:
   - Connect motor controller to computer via USB/Serial
   - Ensure motor controller is powered on
   - The application will automatically detect the connection

2. **Launch Application**:
   - Use desktop shortcut or launcher script
   - Application will auto-detect COM port and establish connection

### Basic Operation

#### Setting Test Parameters

**Motor Control Parameters**:
- **Target RPM**: Desired motor speed (default: 320 RPM)
- **Forward Torque**: Torque percentage for forward rotation (default: 100%)
- **Reverse Torque**: Torque percentage for reverse test (default: -100%)
- **Forward Duration**: Time to apply forward torque (default: 5 seconds)
- **Reverse Duration**: Time to apply reverse torque (default: 3 seconds)

**Safety Limits**:
- **Max Motor Current**: Maximum allowable motor current (default: 100A)
- **Max Brake Current**: Maximum braking current (default: 100A)

#### Running Tests

1. **Configure Parameters**: Set your desired test parameters
2. **Set Cycle Count**:
   - Enter `-1` for continuous testing
   - Enter specific number for fixed cycle count
3. **Start Test**: Click "Start" button
4. **Monitor Progress**: Watch real-time parameters and status lights
5. **Stop Test**: Click "Stop" to halt testing at any time

### Understanding the Interface

#### Status Lights
- **Green Light**: System ready or running normally
- **Yellow Light**: Warning condition detected
- **Red Light**: Fault condition or system stopped

#### Real-Time Parameters
- **Motor RPM**: Current motor rotation speed
- **Motor Current**: Current draw by motor
- **Motor Temperature**: Motor housing temperature
- **Controller Temperature**: Motor controller temperature
- **Battery Voltage**: Supply voltage level
- **Battery Current**: Battery current draw

#### Fault and Warning Display
- **Active Faults**: Critical errors that stop motor operation
- **Active Warnings**: Non-critical alerts for monitoring
- **Register Values**: Raw hexadecimal values for debugging

## Configuration

### Automatic Configuration
The application automatically detects:
- Available serial/COM ports
- Operating system type
- Motor controller connection
- System directories for data storage

### Manual Configuration
Advanced users can modify `src/config.py`:

```python
# Motor connection settings
MOTOR_SETTINGS = {
    'port': 'COM3',  # or '/dev/ttyUSB0' for Linux
    'slave_address': 1,
    'baudrate': 115200,
    # ... other settings
}

# Test parameters
DEFAULT_TEST_PARAMS = {
    "forward_torque": 100,
    "forward_duration": 5,
    "reverse_torque": -100,
    "reverse_duration": 2,
    # ... other parameters
}
```

## Common Installation Issues & Solutions

### "Python was not found" Error

This is the most common issue on Windows. Here's how to fix it:

#### Solution 1: Use Python Launcher
```cmd
py --version
py install.py
```

#### Solution 2: Install Python (First Time Users)

**Windows - Method A (Recommended)**:
1. Press `Win + S`, search "Microsoft Store"
2. Search for "Python 3.12"
3. Click "Install"
4. After installation, restart command prompt
5. Run: `python install.py`

**Windows - Method B**:
1. Visit [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.12+ for Windows
3. **IMPORTANT**: Check "Add Python to PATH" during installation
4. Restart command prompt
5. Run: `python install.py`

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 install.py
```

**Linux (CentOS/RHEL)**:
```bash
sudo yum install python3 python3-pip
python3 install.py
```

#### Solution 3: Find Existing Python Installation
```cmd
# Search for Python on your system
where python /R C:\
# or
dir "C:\Program Files\Python*" /AD
```

### Other Common Issues

#### "No serial ports found"
**Solution**:
1. Check USB/serial cable connection
2. Verify motor controller is powered on
3. On Linux, ensure user is in `dialout` group:
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and back in
   ```

#### "Failed to initialize motor controller"
**Solution**:
1. Verify correct baudrate (default: 115200)
2. Check slave address setting (default: 1)
3. Try different COM port if multiple available
4. Restart motor controller

#### Application won't start
**Solution**:
1. Re-run the installer:
   ```bash
   python install.py
   ```
2. Check Python version (requires 3.7+)
3. Try manual installation method

#### Permission denied (Linux)
**Solution**:
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Make launcher executable
chmod +x OneWayClutchTester.sh
# Log out and back in
```

### Advanced Troubleshooting

#### Check Log Files
Logs are stored in:
- **Windows**: `Documents/OneWayClutchTester/logs/`
- **Linux**: `~/one_way_clutch_data/logs/`

#### Test Serial Connection
```bash
# Activate virtual environment first
python -c "from src.config import auto_detect_com_port; print(auto_detect_com_port())"
```

#### Reset Application
```bash
# Stop all processes and restart
rm -rf venv/  # Remove virtual environment
python install.py  # Reinstall
```

## Understanding Test Results

### Successful One-Way Clutch Operation
- **Forward Phase**: Motor rotates in positive direction
- **Reverse Phase**: Motor should NOT rotate (clutch prevents reverse)
- **Cycle Count**: Increments only when both phases complete successfully

### One-Way Clutch Failure Indicators
- **Reverse Rotation Detected**: Critical failure - clutch is worn out
- **Excessive Reverse Duration**: Warning - clutch may be wearing
- **Temperature Spikes**: Indicates mechanical stress

### Data Output
- **Cycle Count File**: `No_of_cycles.txt` stores completed cycle counts
- **Log Files**: Detailed operation logs with timestamps
- **Real-time Display**: Live parameters during testing

## Technical Details

### Communication Protocol
- **Protocol**: Modbus RTU over serial
- **Baudrate**: 115200 bps
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1

### Motor Control Registers
- **Speed Command**: Register 1677
- **Torque Command**: Register 494
- **State Command**: Register 493
- **Fault Registers**: 258, 299
- **Warning Registers**: 277, 359

### Fault Recovery System
The application includes a sophisticated 4-stage fault recovery system:
1. **Stage 1**: 5 attempts, 60-second intervals
2. **Stage 2**: 5 attempts, 5-minute intervals  
3. **Stage 3**: 5 attempts, 15-minute intervals
4. **Stage 4**: 5 attempts, 30-minute intervals

## Development

### Project Structure
```
OneWayClutchTester/
├── install.py              # Setup script
├── requirements.txt        # Python dependencies
├── src/                    # Source code
│   ├── __init__.py        # Package marker
│   ├── gui.py             # Main GUI application
│   ├── motor_controller.py # Motor control logic
│   └── config.py          # Configuration and auto-detection
├── assets/                 # Resources
│   └── download.png       # Application logo
└── README.md              # This file
```

### Running in Development Mode
```bash
# Activate virtual environment
source venv/bin/activate     # Linux
venv\Scripts\activate.bat    # Windows

# Run application directly
python src/gui.py

# Run with debug logging
python src/gui.py --debug
```

### Adding New Features
1. **Motor Parameters**: Add to `PARAMETER_CONFIG` in `config.py`
2. **GUI Elements**: Modify `create_gui()` method in `gui.py`
3. **Commands**: Add to `COMMANDS` dictionary in `config.py`

### Testing
```bash
# Test motor controller connection
python src/motor_controller.py --port COM3 --cycles 5

# Test configuration detection
python -c "from src.config import get_system_info; print(get_system_info())"
```

## Support

### Getting Help

1. **Check Logs**: Review log files in data directory for error details
2. **Verify Hardware**: Ensure all connections and power are correct
3. **Re-run Setup**: Try `python install.py` again
4. **Check Permissions**: Ensure proper serial port access

### Reporting Issues

When reporting issues, please include:
- Operating system and version
- Python version (`python --version`)
- Error messages from log files
- Hardware configuration details
- Steps to reproduce the issue

### Log File Locations
- **Windows**: `%USERPROFILE%\Documents\OneWayClutchTester\logs\`
- **Linux**: `~/one_way_clutch_data/logs/`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built for bicycle hub motor testing applications
- Designed for reliability in industrial testing environments
- Supports continuous operation for durability testing

---

**Quick Setup Summary**:
```bash
git clone <repository-url>
cd OneWayClutchTester
python install.py
# Double-click desktop shortcut to run
```
