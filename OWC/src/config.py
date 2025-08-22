import os
import platform
import serial.tools.list_ports
import logging
from pathlib import Path
import minimalmodbus

def get_system_info():
    """Enhanced system information detection"""
    system = platform.system().lower()
    is_windows = system == 'windows'
    is_linux = system == 'linux'

    # More robust Raspberry Pi detection
    is_raspberry_pi = False
    if is_linux:
        try:
            # Check multiple ways to detect RPi
            rpi_indicators = [
                'raspberry' in platform.platform().lower(),
                os.path.exists('/proc/device-tree/model') and 'raspberry' in open(
                    '/proc/device-tree/model').read().lower(),
                os.path.exists('/boot/config.txt'),
                'arm' in platform.machine().lower()
            ]
            is_raspberry_pi = any(rpi_indicators)
        except:
            pass

    return {
        'system': system,
        'is_windows': is_windows,
        'is_linux': is_linux,
        'is_raspberry_pi': is_raspberry_pi,
        'architecture': platform.machine(),
        'python_version': platform.python_version()
    }


def auto_detect_com_port():
    """Automatically detect and validate available COM/serial ports"""
    system_info = get_system_info()
    available_ports = serial.tools.list_ports.comports()

    if not available_ports:
        logging.warning("No serial ports found")
        return None

    # Test each port for actual connectivity
    for port in available_ports:
        if test_port_connection(port.device):
            logging.info(f"Successfully connected to port: {port.device} - {port.description}")
            return port.device

    # If no port responds, return the first available as fallback
    if available_ports:
        fallback_port = available_ports[0].device
        logging.warning(f"No responding ports found, using fallback: {fallback_port}")
        return fallback_port

    return None


def test_port_connection(port_name, timeout=2):
    """Test if a port can be opened and basic communication works"""
    try:
        import minimalmodbus
        # Try to create a connection
        test_instrument = minimalmodbus.Instrument(port_name, 1)
        test_instrument.serial.baudrate = MOTOR_SETTINGS['baudrate']
        test_instrument.serial.timeout = timeout

        # Try a simple read operation (this will fail gracefully if no device)
        try:
            test_instrument.read_register(258, 0)  # Try reading fault register
            return True
        except:
            # Even if read fails, if port opened successfully, it's valid
            return True

    except Exception as e:
        logging.debug(f"Port {port_name} test failed: {e}")
        return False
    finally:
        try:
            if 'test_instrument' in locals():
                test_instrument.serial.close()
        except:
            pass



def get_data_directories():
    """Get appropriate directories for data storage based on OS"""
    system_info = get_system_info()

    if system_info['is_windows']:
        # Use Documents folder on Windows
        base_dir = Path.home() / "Documents" / "OneWayClutchTester"
    else:
        # Use home directory on Linux
        base_dir = Path.home() / "one_way_clutch_data"

    # Create directories if they don't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)

    return {
        'base_dir': str(base_dir),
        'logs_dir': str(logs_dir),
        'data_dir': str(data_dir)
    }


def get_logo_path():
    """Get the correct logo path based on current directory structure"""
    current_dir = Path(__file__).parent
    possible_paths = [
        current_dir / "assets" / "download.png",
        current_dir / "download.png",
        current_dir.parent / "assets" / "download.png",
        current_dir.parent / "download.png"
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    logging.warning("Logo file not found")
    return None


# Get system-specific configurations
SYSTEM_INFO = get_system_info()
DATA_DIRS = get_data_directories()
AUTO_DETECTED_PORT = auto_detect_com_port()

# Motor connection settings with auto-detection
MOTOR_SETTINGS = {
    'port': AUTO_DETECTED_PORT or ('/dev/ttyUSB0' if SYSTEM_INFO['is_linux'] else 'COM3'),
    'slave_address': 1,
    'baudrate': 115200,
    'bytesize': 8,
    'parity': 'N',
    'stopbits': 1,
    'timeout': 1,
    'fault_recovery_time': 60,
    'max_fault_recovery_attempts': 5,
}

COMMANDS = {
    "set_speed_regulator_mode": {"address": 11},
    "set_remote_torque_command": {"address": 494, "multiplier": 40.46, "max_register_value": 2 ** 16},
    "set_remote_maximum_regen_battery_current_limit": {"address": 361, "multiplier": 8},
    "set_remote_maximum_battery_current_limit": {"address": 360, "multiplier": 8},
    "set_remote_maximum_motoring_current": {"address": 491, "multiplier": 40.96},
    "set_remote_maximum_braking_current": {"address": 492, "multiplier": 40.96},
    "set_remote_maximum_braking_torque": {"address": 1680, "multiplier": 40.96},
    "set_remote_speed_command": {"address": 1677, "max_register_value": 2 ** 16},
    "set_remote_state_command": {"address": 493},
    "read_faults": {"address": 258, "multiplier": 1},
    "read_faults2": {"address": 299, "multiplier": 1},
    "read_warnings": {"address": 277, "multiplier": 1},
    "read_warnings2": {"address": 359, "multiplier": 1},
    "clear_faults": {"address": 508,"multiplier": 1},
}

PARAMETER_CONFIG = {
    "motor_temp": {"address": 261, "multiplier": 1},
    "controller_temp": {"address": 259, "multiplier": 1},
    "battery_voltage": {"address": 265, "multiplier": 0.03},
    "battery_state of charge": {"address": 267, "multiplier": 1},
    "motor_rpm": {"address": 263, "multiplier": 1},
    "motor_current": {"address": 262, "multiplier": 0.032},
    "battery_current": {"address": 266, "multiplier": 0.032},
    "read_faults":{"address":258, "multiplier": 1},
    "read_faults2":{"address":299, "multiplier": 1},
    "read_warnings":{"address":277, "multiplier": 1},
    "read_warnings2":{"address":359, "multiplier": 1},
}

FAULT_DESCRIPTIONS = {
    0: "Controller over voltage (flash code 1,1)",
    1: "Phase over current (flash code 1,2)",
    2: "Current sensor calibration (flash code 1,3)",
    3: "Current sensor over current (flash code 1,4)",
    4: "Controller over temperature (flash code 1,5)",
    5: "Motor Hall sensor fault (flash code 1,6)",
    6: "Controller under voltage (flash code 1,7)",
    7: "POST static gating test (flash code 1,8)",
    8: "Network communication timeout (flash code 2,1)",
    9: "Instantaneous phase over current (flash code 2,2)",
    10: "Motor over temperature (flash code 2,3)",
    11: "Throttle voltage outside range (flash code 2,4)",
    12: "Instantaneous controller over voltage (flash code 2,5)",
    13: "Internal error (flash code 2,6)",
    14: "POST dynamic gating test (flash code 2,7)",
    15: "Instantaneous under voltage (flash code 2,8)"
}

FAULT2_DESCRIPTIONS = {
    0: "Parameter CRC (flash code 3,1)",
    1: "Current Scaling (flash code 3,2)",
    2: "Voltage Scaling (flash code 3,3)",
    3: "Headlight Undervoltage (flash code 3,4)",
    4: "Parameter 3 CRC (flash code 3,5)",
    5: "CAN bus (flash code 3,6)",
    6: "Hall Stall (flash code 3,7)",
    7: "Bootloader - Not used (flash code 3,8)",
    8: "Parameter2CRC (flash code 4,1)",
    9: "Hall vs Sensorless position > 30deg (flash code 4,2)",
    10: "Dynamic torque sensor voltage outside range (flash code 4,3)",
    11: "Dynamic Torque Sensor Static Voltage Fault (flash code 4,4)",
    12: "Remote CAN fault (flash code 4,5)",
    13: "Accelerometer Side Tilt fault (flash code 4,6)",
    14: "Open Phase Fault (flash code 4,7)",
    15: "Analog brake voltage out of range (flash code 4,8)"
}

WARNING_DESCRIPTIONS = {
    0: "Communication Timeout (flash code 5,1)",
    1: "Hall Sensor (flash code 5,2)",
    2: "Hall stall (flash code 5,3)",
    3: "Wheel Speed Sensor (flash code 5,4)",
    4: "CAN Bus (flash code 5,5)",
    5: "Hall Illegal sector (flash code 5,6)",
    6: "Hall illegal transition (flash code 5,7)",
    7: "Low battery voltage foldback (flash code 5,8)",
    8: "High battery voltage foldback (flash code 6,1)",
    9: "Motor temperature foldback (flash code 6,2)",
    10: "Controller over temperature foldback (flash code 6,3)",
    11: "Low Battery SOC foldback (flash code 6,4)",
    12: "High Battery SOC foldback (flash code 6,5)",
    13: "12T overload foldback (flash code 6,6)",
    14: "Low temperature Battery/Controller foldback (flash code 6,7)",
    15: "BMS communication timeout (flash code 6,8)"
}

WARNING2_DESCRIPTIONS = {
    0: "Throttle out of range (flash code 7,1)",
    1: "Dual speed sensor missing pulses (flash code 7,2)",
    2: "Dual speed sensor no pulses (flash code 7,3)",
    3: "Dynamic Flash Full (flash code 7,4)",
    4: "Dynamic Flash Read Error (flash code 7,5)",
    5: "Dynamic Flash Write Error (flash code 7,6)",
    6: "Parameters3 missing (flash code 7,7)",
    7: "Missed CAN Message (flash code 7,8)",
    8: "High Battery temperature foldback (flash code 8,1)",
    9: "ADC Saturation Event (flash code 8,2)",
    10: "Reserved (flash code 8,3)",
    11: "Reserved (flash code 8,4)",
    12: "Reserved (flash code 8,5)",
    13: "Reserved (flash code 8,6)",
    14: "Reserved (flash code 8,7)",
    15: "Reserved (flash code 8,8)"
}

DEFAULT_TEST_PARAMS = {
    "forward_torque": 100,
    "forward_duration": 5,
    "reverse_torque": -100,
    "reverse_duration": 2,
    "max_motor_current": 70,
    "max_brake_current": 40,
    "target_rpm": 300
}

ONE_WAY_CLUTCH_PARAMS = {
    "max_reverse_rotation_time": 2.5
}

LOGGING_CONFIG = {
    "filename": os.path.join(DATA_DIRS['logs_dir'], "Log_no_of_cycles.log"),
    "filemode": "a",
    "level": "INFO",
    "format": "%(asctime)s - %(message)s"
}

RETRY_CONFIG = {
    "max_retries": 3,
    "retry_delay": 1
}

FILE_NAMES = {
    "cycle_count": os.path.join(DATA_DIRS['data_dir'], "No_of_cycles.txt")
}

# Recovery stages with attempts and intervals (in seconds)
RECOVERY_STAGES = [
    {"attempts": 5, "interval": 60},   # Stage 1: 60 seconds
    {"attempts": 5, "interval": 300},  # Stage 2: 300 seconds (5 minutes)
    {"attempts": 5, "interval": 900},  # Stage 3: 900 seconds (15 minutes)
    {"attempts": 5, "interval": 1800}, # Stage 4: 1800 seconds (30 minutes)
]

# Initial wait time before recovery
INITIAL_WAIT_TIME = 10

# Logo path
LOGO_PATH = get_logo_path()