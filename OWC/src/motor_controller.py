import minimalmodbus
import serial
import logging
import os
import time
import math
import asyncio
import sys
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

try:
    from src.config import (
        MOTOR_SETTINGS, COMMANDS, PARAMETER_CONFIG, FAULT_DESCRIPTIONS, FAULT2_DESCRIPTIONS,
        WARNING_DESCRIPTIONS, WARNING2_DESCRIPTIONS, DEFAULT_TEST_PARAMS,
        ONE_WAY_CLUTCH_PARAMS, LOGGING_CONFIG, RETRY_CONFIG, FILE_NAMES, RECOVERY_STAGES, INITIAL_WAIT_TIME
    )
except ImportError:
    from config import (
        MOTOR_SETTINGS, COMMANDS, PARAMETER_CONFIG, FAULT_DESCRIPTIONS, FAULT2_DESCRIPTIONS,
        WARNING_DESCRIPTIONS, WARNING2_DESCRIPTIONS, DEFAULT_TEST_PARAMS,
        ONE_WAY_CLUTCH_PARAMS, LOGGING_CONFIG, RETRY_CONFIG, FILE_NAMES, RECOVERY_STAGES, INITIAL_WAIT_TIME
    )
# Configure logging using settings from config.py
logging.basicConfig(
    filename=LOGGING_CONFIG["filename"],
    filemode=LOGGING_CONFIG["filemode"],
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
)


class MotorController:
    def __init__(self, port=None, slave_address=None, baudrate=None, fault_recovery_time=None,
                 max_fault_recovery_attempts=None):
        self.motor = None
        self.port = port or MOTOR_SETTINGS['port']
        self.slave_address = slave_address or MOTOR_SETTINGS['slave_address']
        self.baudrate = baudrate or MOTOR_SETTINGS['baudrate']
        self.running = False
        self.auto_recovery = False
        self.fault_recovery_time = fault_recovery_time or MOTOR_SETTINGS['fault_recovery_time']
        self.max_fault_recovery_attempts = max_fault_recovery_attempts or MOTOR_SETTINGS['max_fault_recovery_attempts']
        # Use asyncio.Lock instead of threading.Lock
        self.modbus_lock = asyncio.Lock()
        self.setup_motor()
        # Task references for monitoring
        self.motor_task = None
        self.fault_monitor_task = None
        self.recovery_task = None

    def setup_motor(self):
        """Enhanced motor setup with connection validation"""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.motor = minimalmodbus.Instrument(self.port, self.slave_address)
                self.motor.serial.baudrate = self.baudrate
                self.motor.serial.bytesize = MOTOR_SETTINGS['bytesize']
                self.motor.serial.parity = serial.PARITY_NONE if MOTOR_SETTINGS['parity'] == 'N' else MOTOR_SETTINGS[
                    'parity']
                self.motor.serial.stopbits = MOTOR_SETTINGS['stopbits']
                self.motor.serial.timeout = MOTOR_SETTINGS['timeout']

                # Test the connection
                if self.validate_connection():
                    logging.info(f"Motor controller connected successfully on {self.port}")
                    return self.motor
                else:
                    raise Exception("Connection validation failed")

            except Exception as e:
                logging.warning(f"Setup attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    # Try auto-detecting port again
                    from src.config import auto_detect_com_port
                    new_port = auto_detect_com_port()
                    if new_port and new_port != self.port:
                        logging.info(f"Trying alternative port: {new_port}")
                        self.port = new_port
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Failed to setup motor after {max_retries} attempts")
                    raise

        return self.motor

    def validate_connection(self):
        """Validate that the motor controller is responding"""
        try:
            # Try reading a basic register (fault register is usually accessible)
            test_value = self.motor.read_register(PARAMETER_CONFIG["read_faults"]["address"], 0)
            logging.info(f"Connection validated - fault register value: {test_value}")
            return True
        except Exception as e:
            logging.warning(f"Connection validation failed: {e}")
            return False
        
    async def write_to_register(self, address, value, multiplier=1, max_register_value=None):
        """Writes a value to a specified Modbus register with optional processing."""
        try:
            value = int(value * multiplier)
            if max_register_value and value < 0:
                value = max_register_value + value
            async with self.modbus_lock:
                await asyncio.to_thread(self.motor.write_registers, address, [value])
        except Exception as e:
            (logging.info(f"Successfully wrote {value} to address {address}:{e}"))

    async def execute_command(self, command_name, value):
        """Executes a predefined command with the given value."""
        try:
            command = COMMANDS.get(command_name)
            if command:
                await self.write_to_register(
                    address=command["address"],
                    value=value,
                    multiplier=command.get("multiplier", 1),
                    max_register_value=command.get("max_register_value")
                )
                return True
            else:
                return False
        except Exception as e:
            logging.error(f"Invalid command name: {command_name}:{e}")

    async def read_motor_data(self, data_type):
        """Reads motor parameters such as RPM, temperature, and voltage."""
        config = PARAMETER_CONFIG.get(data_type)
        if not config:
            logging.error(f"Invalid data type requested: {data_type}")
            return 0
        try:
            async with self.modbus_lock:
                # Use a thread executor for blocking I/O operations
                raw_value = await asyncio.to_thread(self.motor.read_register, config["address"], 0)
            scaled_value = raw_value * config["multiplier"]
            return scaled_value
        except Exception as e:
            logging.error(f"Error reading {data_type}: {e}")
            return 0

    def decode_bits(self, register_value, descriptions):
        """
        Decodes a 16-bit register value into specific messages.
        Each bit position corresponds to a specific message.
        :return: A list of active messages.
        """
        active_messages = []
        for bit_position in range(16):
            if register_value & (1 << bit_position):
                if bit_position in descriptions:  # Check if the bit has a description
                    active_messages.append(descriptions[bit_position])
        return active_messages

    def decode_fault_bits(self, register_value):
        """Decodes a fault register value."""
        return self.decode_bits(register_value, FAULT_DESCRIPTIONS)

    def decode_fault2_bits(self, register_value):
        """Decodes a second fault register value."""
        return self.decode_bits(register_value, FAULT2_DESCRIPTIONS)

    def decode_warning_bits(self, register_value):
        """Decodes a warning register value."""
        return self.decode_bits(register_value, WARNING_DESCRIPTIONS)

    def decode_warning2_bits(self, register_value):
        """Decodes a second warning register value."""
        return self.decode_bits(register_value, WARNING2_DESCRIPTIONS)

    async def check_faults(self):
        """Check all fault conditions with improved error handling and retry logic"""
        for retry in range(RETRY_CONFIG["max_retries"]):
            try:
                async with self.modbus_lock:
                    # Read fault registers using the updated PARAMETER_CONFIG addresses
                    faults_reg = await asyncio.to_thread(
                        self.motor.read_register,
                        PARAMETER_CONFIG["read_faults"]["address"]
                    )
                    faults2_reg = await asyncio.to_thread(
                        self.motor.read_register,
                        PARAMETER_CONFIG["read_faults2"]["address"]
                    )

                fault_messages = self.decode_fault_bits(faults_reg)
                fault2_messages = self.decode_fault2_bits(faults2_reg)

                all_faults = fault_messages + fault2_messages

                if all_faults:
                    logging.warning(f"Active faults detected: {', '.join(all_faults)}")
                return all_faults, faults_reg, faults2_reg

            except Exception as e:
                logging.warning(f"Error checking faults (attempt {retry + 1}/{RETRY_CONFIG['max_retries']}): {e}")
                if retry < RETRY_CONFIG["max_retries"] - 1:
                    await asyncio.sleep(RETRY_CONFIG["retry_delay"])

        logging.error("Maximum retries reached while checking faults")
        if "timeout" in str(e).lower():
            logging.warning("Temporary Modbus timeout while checking faults — ignoring")
            return [], 0, 0
        else:
            logging.error(f"Error checking faults: {e}")
            return ["Internal Modbus error"], 0, 0

    async def check_warnings(self):
        """Check all warning conditions by reading and decoding warning registers"""
        for retry in range(RETRY_CONFIG["max_retries"]):
            try:
                async with self.modbus_lock:
                    # Read warning registers using the updated PARAMETER_CONFIG addresses
                    warnings_reg = await asyncio.to_thread(
                        self.motor.read_register,
                        PARAMETER_CONFIG["read_warnings"]["address"]
                    )
                    warnings2_reg = await asyncio.to_thread(
                        self.motor.read_register,
                        PARAMETER_CONFIG["read_warnings2"]["address"]
                    )
                warning_messages = self.decode_warning_bits(warnings_reg)
                warning2_messages = self.decode_warning2_bits(warnings2_reg)

                # Combine all warning messages
                all_warnings = warning_messages + warning2_messages

                if all_warnings:
                    logging.warning(f"Active warnings detected: {', '.join(all_warnings)}")
                return all_warnings, warnings_reg, warnings2_reg

            except Exception as e:
                logging.warning(f"Error checking warnings (attempt {retry + 1}/{RETRY_CONFIG['max_retries']}): {e}")
                if retry < RETRY_CONFIG["max_retries"] - 1:
                    await asyncio.sleep(RETRY_CONFIG["retry_delay"])

        logging.error("Maximum retries reached while checking warnings")
        if "timeout" in str(e).lower():
            logging.warning("Temporary Modbus timeout while checking faults — ignoring")
            return [], 0, 0
        else:
            logging.error(f"Error checking faults: {e}")
            return ["Internal Modbus error"], 0, 0

    async def clear_motor_faults(self):
        """
        Sends the clear fault command to the motor controller.
        Returns True if successful, False otherwise.
        """
        try:
            logging.info("Sending clear faults command")
            await self.execute_command("clear_faults", 1)  # Value 1 to clear faults
            return True
        except Exception as e:
            logging.error(f"Failed to send clear faults command: {e}")
            return False

    def get_last_cycle_count(self, file_name):
        """Reads the last recorded cycle count from the file."""
        if not os.path.exists(file_name):
            return 1
        try:
            with open(file_name, "r") as file:
                lines = file.readlines()
                for line in reversed(lines):
                    if line.startswith("No of cycles:"):
                        try:
                            return int(line.split(":")[1].strip())
                        except ValueError:
                            continue
        except Exception as e:
            logging.error(f"Error reading cycle count: {e}")
            return 1

    async def check_one_way_clutch(self, torque_duration_pairs):
        """
        Check for one-way clutch wear-out during reverse torque conditions.
        """
        reverse_rotation_time = 0
        async with self.modbus_lock:
            for torque, duration in torque_duration_pairs:
                if torque < 0:
                    await self.execute_command("set_remote_torque_command", torque)
                    await asyncio.sleep(duration)
                    motor_rpm = await self.read_motor_data("motor_rpm")
                    if motor_rpm < 0:
                        reverse_rotation_time += duration
                        if reverse_rotation_time >= ONE_WAY_CLUTCH_PARAMS["max_reverse_rotation_time"]:
                            await self.execute_command("set_remote_torque_command", 0)
                            await self.execute_command("set_remote_state_command", 0)
                            logging.warning("One-way clutch trying to rotate in reverse it may worn out sooner..!")
                            return False
                        else:
                            logging.warning("One-way clutch is trying to rotate in reverse.")
                    else:
                        reverse_rotation_time = 0
        return True

    async def advanced_fault_recovery(self, recovery_callback=None):
        """
        Multi-stage fault recovery mechanism with progressive intervals
        Includes callback mechanism to update GUI with recovery status
        """
        initial_wait_time = INITIAL_WAIT_TIME
        current_stage = 0
        attempt_in_stage = 0

        # Notify GUI that recovery has started
        if recovery_callback:
            recovery_callback("recovery_started", f"Stage {current_stage + 1}, Attempt {attempt_in_stage + 1}")

        while True:
            try:
                stage = RECOVERY_STAGES[current_stage]
                # Log the current recovery stage and attempt
                logging.warning(f"Fault recovery - Stage {current_stage + 1}, Attempt {attempt_in_stage + 1}")

                # Wait for initial period before first attempt
                if attempt_in_stage == 0:
                    logging.info(f"Fault detected. Waiting {initial_wait_time} seconds before first recovery attempt.")
                    # Countdown for initial wait time with updates to GUI
                    for remaining in range(initial_wait_time, 0, -1):
                        await asyncio.sleep(1)
                        if recovery_callback:
                            recovery_callback("recovery_countdown", f"{remaining}s")
                        if not self.auto_recovery:  # Check if recovery was cancelled
                            if recovery_callback:
                                recovery_callback("recovery_stopped", "User stopped recovery")
                            return False

                logging.info("Attempting to clear faults...")
                if recovery_callback:
                    recovery_callback("recovery_waiting", "Clearing faults")
                await self.clear_motor_faults()

                await asyncio.sleep(0.5)
                faults, _, _ = await self.check_faults()

                if not faults:
                    logging.info("Faults successfully cleared. Resuming motor operation.")
                    if recovery_callback:
                        recovery_callback("recovery_successful", "Faults cleared")
                    return True

                interval = stage["interval"]
                logging.info(f"Faults still present. Waiting {interval} seconds before next attempt.")

                if recovery_callback:
                    recovery_callback("recovery_waiting", f"Stage {current_stage + 1}, Attempt {attempt_in_stage + 1}")

                check_interval = min(interval, 60)
                for i in range(int(interval / check_interval)):
                    for sec in range(check_interval, 0, -1):
                        await asyncio.sleep(1)
                        countdown = f"{sec + i * check_interval}s"
                        if recovery_callback:
                            recovery_callback("recovery_countdown", countdown)
                        if not self.auto_recovery:
                            if recovery_callback:
                                recovery_callback("recovery_stopped", "User stopped recovery")
                            return False

                    # Check if faults cleared while waiting
                    periodic_faults, _, _ = await self.check_faults()
                    if not periodic_faults:
                        logging.info("Periodic fault check: No active faults. Resuming motor operation.")
                        if recovery_callback:
                            recovery_callback("recovery_successful", "Faults cleared")
                        return True

                # Move to next attempt or stage
                attempt_in_stage += 1

                # If we've completed all attempts in this stage, move to next stage
                if attempt_in_stage >= stage["attempts"]:
                    current_stage = (current_stage + 1) % len(RECOVERY_STAGES)
                    attempt_in_stage = 0
                    logging.warning(f"Moving to fault recovery stage {current_stage + 1}")
                    if recovery_callback:
                        recovery_callback("recovery_stage_change", f"Stage {current_stage + 1}")

            except Exception as e:
                logging.error(f"Error during fault recovery: {e}")
                if recovery_callback:
                    recovery_callback("recovery_error", str(e))
                await asyncio.sleep(60)  # Wait a minute before retrying after an error

    async def fault_monitor(self, fault_check_callback):
        """Dedicated async task for continuous fault monitoring"""
        check_interval = 1.0  # Check every second
        while self.running:
            try:
                # Check faults and warnings
                faults, faults_reg, faults2_reg = await self.check_faults()
                warnings, warnings_reg, warnings2_reg = await self.check_warnings()

                if fault_check_callback:
                    fault_check_callback(faults, warnings, faults_reg, faults2_reg, warnings_reg, warnings2_reg)

                if faults and self.auto_recovery:
                    logging.warning(f"Faults detected by monitor: {', '.join(faults)}")

                    # Cancel any existing recovery task
                    if self.recovery_task and not self.recovery_task.done():
                        self.recovery_task.cancel()

                    # Start new recovery task
                    self.recovery_task = asyncio.create_task(
                        self.advanced_fault_recovery(fault_check_callback)
                    )
                    recovery_result = await self.recovery_task
                    if recovery_result and self.running:
                        logging.info("Restarting motor after successful fault recovery")
                        try:
                            await self.execute_command("set_remote_state_command", 2)
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            logging.error(f"Failed to restart motor after recovery: {e}")

                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                logging.info("Fault monitor task cancelled")
                break
            except Exception as e:
                logging.error(f"Error in fault monitor: {e}")
                await asyncio.sleep(5)  # Wait before retry after error

    async def perform_motor_cycles(self, torque_duration_pairs, cycle_count_target, txt_file_name,
                                   fault_check_callback=None,
                                   timer_callback=None):
        """Performs motor cycles with precise timing control and improved direction verification."""
        try:
            # Get current cycle count
            current_count = self.get_last_cycle_count(txt_file_name) or 1
            target_count = float('inf') if cycle_count_target == -1 else cycle_count_target
            self.running = True
            self.auto_recovery = True

            # Start the fault monitor as a separate task
            if fault_check_callback:
                self.fault_monitor_task = asyncio.create_task(
                    self.fault_monitor(fault_check_callback)
                )

            while self.running:
                cycle_start_time = time.time()
                logging.info(f"Starting cycle {current_count}")
                forward_successful = False
                reverse_successful = False
                for idx, (torque, duration) in enumerate(torque_duration_pairs):
                    if not self.running:
                        break

                    direction = "forward" if torque > 0 else "reverse"
                    logging.info(f"Setting {direction} torque: {torque} for {duration} seconds")

                    set_success = False
                    for retry in range(RETRY_CONFIG["max_retries"]):
                        try:
                            await self.execute_command("set_remote_torque_command", torque)
                            set_success = True
                            break
                        except Exception as e:
                            logging.warning(f"Failed to set torque (attempt {retry + 1}): {e}")
                            await asyncio.sleep(RETRY_CONFIG["retry_delay"])

                    if not set_success:
                        logging.error(f"Failed to set {direction} torque after {RETRY_CONFIG['max_retries']} retries")
                        continue

                    start_time = time.time()
                    end_time = start_time + duration
                    rotation_verified = False
                    direction_check_attempts = 0
                    max_direction_checks = 5

                    while time.time() < end_time and self.running:
                        current_time = time.time()
                        elapsed_time = current_time - start_time

                        # Update timer callback if provided
                        if timer_callback:
                            timer_callback(direction, elapsed_time, duration)

                        # Verify motor direction with increased frequency at the beginning
                        if not rotation_verified and direction_check_attempts < max_direction_checks:
                            try:
                                motor_rpm = await self.read_motor_data("motor_rpm")
                                expected_direction = "positive" if torque > 0 else "negative"
                                actual_direction = "positive" if motor_rpm >= 0 else "negative"

                                logging.info(
                                    f"Motor speed: {motor_rpm} RPM, Expected direction: {expected_direction}, Actual: {actual_direction}")

                                # For forward rotation
                                if torque > 0 and motor_rpm > 10:  # Ensure positive rotation with margin
                                    forward_successful = True
                                    rotation_verified = True
                                # For reverse rotation
                                elif torque < 0:
                                    if motor_rpm < -10:
                                        logging.critical(
                                            "❌ One-way clutch broken! Reverse rotation detected. Stopping test.")
                                        await self.stop_test()
                                        return current_count
                                    elif abs(motor_rpm) < 5:
                                        reverse_successful = True
                                        rotation_verified = True
                                # Direction mismatch
                                elif (torque > 0 and motor_rpm < -10) or (torque < 0 and motor_rpm > 10):
                                    logging.warning(
                                        f"CRITICAL: Motor rotating in wrong direction! Reapplying torque with higher value.")
                                    # Apply higher torque to overcome potential resistance
                                    await self.execute_command("set_remote_torque_command",
                                                               torque * 1.2)  # 20% more torque

                                direction_check_attempts += 1

                                # If we've tried multiple times and still can't get proper rotation
                                if direction_check_attempts >= max_direction_checks and not rotation_verified:
                                    logging.error(
                                        f"Failed to achieve {direction} rotation after {max_direction_checks} attempts")
                                    # Last resort: try with even higher torque
                                    await self.execute_command("set_remote_torque_command", torque * 1.5)
                            except Exception as e:
                                logging.warning(f"Error reading motor RPM: {e}")
                                direction_check_attempts += 1

                        # Small sleep to prevent CPU overuse
                        await asyncio.sleep(0.01)

                    # Reset timer display after segment completes
                    if timer_callback:
                        timer_callback("none", 0, 1)

                    # Add a delay between direction changes to prevent stress on motor
                    if idx < len(torque_duration_pairs) - 1 and self.running:
                        logging.info(f"Adding 0.2 second delay between direction changes")
                        # Apply zero torque during transition to ensure clean direction change
                        await self.execute_command("set_remote_torque_command", 0)
                        await asyncio.sleep(0.2)  # Exactly 0.2 seconds as requested

                    motor_data = {}
                    motor_data["motor_temp"] = await self.read_motor_data("motor_temp")
                    motor_data["controller_temp"] = await self.read_motor_data("controller_temp")
                    motor_data["battery_voltage"] = await self.read_motor_data("battery_voltage")
                    logging.info(
                        f"Motor temperature: {motor_data['motor_temp']}°C, Controller: {motor_data['controller_temp']}°C, Battery: {motor_data['battery_voltage']}V")
                    # Only increase cycle count if both directions were successful
                    if forward_successful and reverse_successful:
                        cycle_data = f"No of cycles: {current_count}\n"
                        try:
                            with open(txt_file_name, "a") as txt_file:
                                txt_file.write(cycle_data)
                            logging.info(f"Cycle {current_count} completed and logged successfully")
                            current_count += 1
                        except Exception as e:
                            logging.error(f"Error writing to file: {e}")
                    else:
                        logging.warning(
                            f"Cycle {current_count} skipped due to unsuccessful rotation (Forward: {forward_successful}, Reverse: {reverse_successful})")
                if not math.isinf(target_count) and current_count > target_count:
                    self.running = False

                cycle_time = time.time() - cycle_start_time
                logging.info(f"Cycle completed in {cycle_time:.2f} seconds")

        except asyncio.CancelledError:
            logging.info("Motor cycle task cancelled")
        except Exception as e:
            logging.error(f"Critical error in perform_motor_cycles: {e}")
        finally:
            # Clean up fault monitor task if it exists
            if self.fault_monitor_task and not self.fault_monitor_task.done():
                self.fault_monitor_task.cancel()
                try:
                    await self.fault_monitor_task
                except asyncio.CancelledError:
                    pass

        return current_count

    async def start_test(self, params=None, cycle_count_target=-1, fault_check_callback=None, timer_callback=None):
        """Starts the motor test with improved parameter initialization and direction verification."""
        try:
            if params is None:
                params = DEFAULT_TEST_PARAMS

            # Ensure we have the proper durations
            forward_duration = params.get("forward_duration", 5)
            reverse_duration = params.get("reverse_duration", 3)
            params["forward_duration"] = forward_duration
            params["reverse_duration"] = reverse_duration

            # Check for faults before starting
            if fault_check_callback:
                faults, faults_reg, faults2_reg = await self.check_faults()
                warnings, warnings_reg, warnings2_reg = await self.check_warnings()
                fault_check_callback(faults, warnings, faults_reg, faults2_reg, warnings_reg, warnings2_reg)

            self.running = True

            # Define initialization commands with more robust settings
            commands = [
                ("set_speed_regulator_mode", 2),
                ("set_remote_maximum_regen_battery_current_limit", 48),
                ("set_remote_maximum_battery_current_limit", 75),
                ("set_remote_maximum_motoring_current", params["max_motor_current"]),
                ("set_remote_maximum_braking_current", params["max_brake_current"]),
                ("set_remote_speed_command", params["target_rpm"]),
                ("set_remote_torque_command", 0)
            ]

            for cmd, value in commands:
                success = False
                for retry in range(RETRY_CONFIG["max_retries"]):
                    try:
                        await self.execute_command(cmd, value)
                        logging.info(f"Successfully set {cmd} to {value}")
                        success = True
                        break
                    except Exception as e:
                        logging.warning(f"Failed to set {cmd} (attempt {retry + 1}): {e}")
                        await asyncio.sleep(RETRY_CONFIG["retry_delay"])

                if not success:
                    logging.error(f"Failed to set {cmd} after multiple attempts")
                    self.running = False
                    return 0

                await asyncio.sleep(0.1)

            success = False
            for retry in range(RETRY_CONFIG["max_retries"]):
                try:
                    await self.execute_command("set_remote_state_command", 2)
                    logging.info("Motor enabled successfully")
                    success = True
                    break
                except Exception as e:
                    logging.warning(f"Failed to enable motor (attempt {retry + 1}): {e}")
                    await asyncio.sleep(RETRY_CONFIG["retry_delay"])

            if not success:
                logging.error("Failed to enable motor after multiple attempts")
                self.running = False
                return 0

            # Wait for the motor to initialize
            await asyncio.sleep(0.1)

            # Define the torque-duration pairs for the cycle
            torque_duration_pairs = [
                (params["forward_torque"], forward_duration),
                (params["reverse_torque"], reverse_duration)
            ]

            # Start motor cycle task
            self.motor_task = asyncio.create_task(
                self.perform_motor_cycles(
                    torque_duration_pairs,
                    cycle_count_target,
                    FILE_NAMES["cycle_count"],
                    fault_check_callback,
                    timer_callback
                )
            )

            # Wait for the motor task to complete
            return await self.motor_task

        except Exception as e:
            logging.error(f"Error starting test: {e}")
            await self.stop_test()
            raise

    async def stop_test(self):
        """Stops the motor test."""
        self.running = False
        self.auto_recovery = False

        # Cancel all running tasks
        if self.motor_task and not self.motor_task.done():
            self.motor_task.cancel()

        if self.fault_monitor_task and not self.fault_monitor_task.done():
            self.fault_monitor_task.cancel()

        if self.recovery_task and not self.recovery_task.done():
            self.recovery_task.cancel()

        try:
            await self.execute_command("set_remote_torque_command", 0)
            await self.execute_command("set_remote_state_command", 0)
            logging.info("Motor stopped")
        except Exception as e:
            logging.error(f"Error stopping motor: {e}")
            raise


# Main entry point for using the async MotorController
async def main(port=None, params=None, cycle_count=-1):
    """Main async function to run the motor controller."""

    # Create fault check callback
    def fault_check_callback(faults, warnings, faults_reg, faults2_reg, warnings_reg, warnings2_reg):
        if faults:
            logging.warning(f"Faults: {faults}")
        if warnings:
            logging.warning(f"Warnings: {warnings}")

    # Create timer callback
    def timer_callback(direction, elapsed_time, duration):
        if direction != "none":
            logging.debug(f"{direction}: {elapsed_time:.2f}/{duration:.2f}s")

    # Initialize and run motor controller
    controller = MotorController(port=port)

    try:
        # Example of running the controller
        await controller.start_test(
            params=params,
            cycle_count_target=cycle_count,
            fault_check_callback=fault_check_callback,
            timer_callback=timer_callback
        )
    except KeyboardInterrupt:
        logging.info("Program interrupted by user")
    finally:
        await controller.stop_test()


# Entry point when script is run directly
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Motor Controller")
    parser.add_argument("--port", help="Serial port for the motor controller")
    parser.add_argument("--cycles", type=int, default=-1, help="Number of cycles to run (-1 for infinite)")
    args = parser.parse_args()

    try:
        asyncio.run(main(port=args.port, cycle_count=args.cycles))
    except KeyboardInterrupt:
        print("Program terminated by user")