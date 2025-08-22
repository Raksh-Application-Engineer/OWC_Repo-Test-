import logging
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, scrolledtext
from PIL import Image, ImageTk
import asyncio
import threading
import sys
import os
from pathlib import Path
# Add src to path if running from project root
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

try:
    from src.motor_controller import MotorController
except ImportError:
    # Fallback for different execution contexts
    from motor_controller import MotorController

class OneWayClutchTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("One-Way Clutch Tester")
        self.root.geometry("1000x900")  # Increased height for fault display
        # Initialize variables
        self.init_variables()
        # Create GUI elements
        self.create_gui()
        # Event loop management
        self.loop = asyncio.new_event_loop()
        self.loop_thread = None
        # Controller reference
        self.motor_controller = None
        # Tasks
        self.parameter_update_task = None
        self.test_task = None

        # Initialize controller in async loop
        self.create_background_loop()
        self.loop.call_soon_threadsafe(self.async_init_controller)

    def get_logo_path(self):
        """Find logo path from various possible locations"""
        current_dir = Path(__file__).parent
        possible_paths = [
            # From src/ directory
            current_dir.parent / "assets" / "download.png",
            # From project root
            current_dir / "assets" / "download.png",
            # Legacy paths
            current_dir / "download.png",
            current_dir.parent / "download.png"
        ]

        for path in possible_paths:
            if path.exists():
                return str(path)

        logging.warning("Logo file not found in any expected location")
        return None

    def create_background_loop(self):
        """Create and start a background thread for the asyncio event loop"""

        def run_event_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self.loop_thread = threading.Thread(target=run_event_loop, args=(self.loop,), daemon=True)
        self.loop_thread.start()

    def async_init_controller(self):
        """Initialize the motor controller in the asyncio loop"""

        async def init():
            try:
                self.motor_controller = MotorController()
                # Start parameters update loop
                self.parameter_update_task = asyncio.create_task(self.async_update_parameters())
            except Exception as e:
                self.root.after(0, lambda err=e: messagebox.showerror("Error",
                                                                      f"Failed to initialize motor controller: {err}"))
        asyncio.create_task(init())

    def init_variables(self):
        """Initialize all GUI variables"""
        self.target_cycles = tk.StringVar(value="-1")
        self.running = False
        self.current_cycle = tk.StringVar(value="0")
        self.motor_rpm = tk.StringVar(value="0")
        self.motor_current = tk.StringVar(value="0")
        self.controller_temp = tk.StringVar(value="0")
        self.motor_temp = tk.StringVar(value="0")
        self.battery_voltage = tk.StringVar(value="0")
        self.battery_current = tk.StringVar(value="0")
        self.status_message = tk.StringVar(value="System Ready")

        # Fault and warning variables
        self.active_faults = []
        self.active_warnings = []
        self.fault_reg_value = tk.StringVar(value="0")
        self.fault2_reg_value = tk.StringVar(value="0")
        self.warning_reg_value = tk.StringVar(value="0")
        self.warning2_reg_value = tk.StringVar(value="0")
        self.recovery_countdown = tk.StringVar(value="")
        self.recovery_status = tk.StringVar(value="")

        # Control parameters
        self.target_rpm = tk.StringVar(value="320")
        self.forward_torque = tk.StringVar(value="100")
        self.reverse_torque = tk.StringVar(value="-100")
        self.forward_duration = tk.StringVar(value="5")
        self.reverse_duration = tk.StringVar(value="3")
        self.max_motor_current = tk.StringVar(value="100")
        self.max_brake_current = tk.StringVar(value="100")

        # Timer variables
        self.current_direction = tk.StringVar(value="None")
        self.direction_timer = tk.StringVar(value="0.0")
        self.direction_progress = tk.DoubleVar(value=0)

    def create_gui(self):
        """Build GUI with dynamic, centered, and responsive layout"""

        self.root.title("One-Way Clutch Tester")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 800)

        # ✅ Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ✅ Header Section
        header_frame = tk.Frame(main_container)
        header_frame.pack(pady=10)

        try:
            logo_path = self.get_logo_path()
            if logo_path:
                logo_img = Image.open(logo_path)
                logo_image = logo_img.resize((200, 133))
                self.logo_photo = ImageTk.PhotoImage(logo_image)
                logo_label = tk.Label(header_frame, image=self.logo_photo)
                logo_label.pack()
        except Exception as e:
            logging.error(f"Error loading logo: {e}")

        title_label = tk.Label(header_frame, text="One-Way Clutch Tester", font=("Arial", 28, "bold"))
        title_label.pack()

        # ✅ Parameters Frame
        params_frame = tk.Frame(main_container)
        params_frame.pack(fill="x", pady=5)

        # Motor Parameters
        motor_frame = tk.LabelFrame(params_frame, text="Motor Parameters", height=150)
        motor_frame.pack(side="left", padx=5, fill="both", expand=True)
        motor_frame.pack_propagate(False)

        self.create_param_row(motor_frame, "Motor RPM:", self.motor_rpm, "RPM", readonly=True)
        self.create_param_row(motor_frame, "Motor Current:", self.motor_current, "Amps", readonly=True)

        # Controller Parameters
        controller_frame = tk.LabelFrame(params_frame, text="Controller Parameters", height=150)
        controller_frame.pack(side="left", padx=5, fill="both", expand=True)
        controller_frame.pack_propagate(False)

        self.create_param_row(controller_frame, "Controller Temp:", self.controller_temp, "°C", readonly=True)
        self.create_param_row(controller_frame, "Motor Temp:", self.motor_temp, "°C", readonly=True)

        # Battery Parameters
        battery_frame = tk.LabelFrame(params_frame, text="Battery Parameters", height=150)
        battery_frame.pack(side="left", padx=5, fill="both", expand=True)
        battery_frame.pack_propagate(False)

        self.create_param_row(battery_frame, "Battery Current:", self.battery_current, "Amps", readonly=True)
        self.create_param_row(battery_frame, "Battery Voltage:", self.battery_voltage, "V", readonly=True)

        # ✅ Control Parameters Frame
        control_params_frame = tk.LabelFrame(main_container, text="Control Parameters")
        control_params_frame.pack(fill="x", pady=10, padx=5)

        left_control = tk.Frame(control_params_frame)
        left_control.pack(side="left", fill="both", expand=True, padx=5)

        right_control = tk.Frame(control_params_frame)
        right_control.pack(side="left", fill="both", expand=True, padx=5)

        self.create_param_row(left_control, "Target RPM:", self.target_rpm, "RPM")
        self.create_param_row(left_control, "Forward Torque:", self.forward_torque, "%")
        self.create_param_row(left_control, "Forward Duration:", self.forward_duration, "sec")

        self.create_param_row(right_control, "Max Motor Current:", self.max_motor_current, "A")
        self.create_param_row(right_control, "Reverse Torque:", self.reverse_torque, "%")
        self.create_param_row(right_control, "Reverse Duration:", self.reverse_duration, "sec")

        # ✅ Cycles Section
        cycles_frame = tk.Frame(main_container)
        cycles_frame.pack(fill="x", pady=10)

        tk.Label(cycles_frame, text="Target Cycles (-1 for continuous):", font=("Arial", 10, "bold")).pack(side="left",
                                                                                                           padx=5)
        tk.Entry(cycles_frame, textvariable=self.target_cycles, width=10).pack(side="left", padx=5)
        tk.Label(cycles_frame, text="Total Number of Cycles Completed:", font=("Arial", 10, "bold")).pack(side="left",
                                                                                                          padx=5)
        tk.Entry(cycles_frame, textvariable=self.current_cycle, state="readonly", width=10).pack(side="left")

        # ✅ Control Buttons
        button_frame = tk.Frame(main_container)
        button_frame.pack(pady=5)

        self.start_button = tk.Button(button_frame, text="Start", command=self.start_test, width=15)
        self.start_button.pack(side="left", padx=10)

        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_test, width=15)
        self.stop_button.pack(side="left", padx=10)

        # ✅ Fault & Warning Display
        fault_frame = tk.LabelFrame(main_container, text="Fault and Warning Monitor")
        fault_frame.pack(fill="both", expand=True, pady=5, padx=5)

        fault_column = tk.Frame(fault_frame)
        fault_column.pack(side="left", fill="both", expand=True, padx=5)

        warning_column = tk.Frame(fault_frame)
        warning_column.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(fault_column, text="Active Faults:", font=("Arial", 10, "bold"), fg="red").pack(anchor="w")
        self.fault_display = scrolledtext.ScrolledText(fault_column, height=4, width=40, bg="#ffeeee", fg="red")
        self.fault_display.pack(fill="both", expand=True, pady=5)

        reg_frame = tk.Frame(fault_column)
        reg_frame.pack(fill="x", pady=2)
        tk.Label(reg_frame, text="Fault Register:").pack(side="left")
        tk.Entry(reg_frame, textvariable=self.fault_reg_value, width=6, state="readonly").pack(side="left", padx=5)
        tk.Label(reg_frame, text="Fault2 Register:").pack(side="left")
        tk.Entry(reg_frame, textvariable=self.fault2_reg_value, width=6, state="readonly").pack(side="left", padx=5)

        tk.Label(warning_column, text="Active Warnings:", font=("Arial", 10, "bold"), fg="orange").pack(anchor="w")
        self.warning_display = scrolledtext.ScrolledText(warning_column, height=4, width=40, bg="#fff8ee", fg="orange")
        self.warning_display.pack(fill="both", expand=True, pady=5)

        reg_frame2 = tk.Frame(warning_column)
        reg_frame2.pack(fill="x", pady=2)
        tk.Label(reg_frame2, text="Warning Register:").pack(side="left")
        tk.Entry(reg_frame2, textvariable=self.warning_reg_value, width=6, state="readonly").pack(side="left", padx=5)
        tk.Label(reg_frame2, text="Warning2 Register:").pack(side="left")
        tk.Entry(reg_frame2, textvariable=self.warning2_reg_value, width=6, state="readonly").pack(side="left", padx=5)

        # ✅ Recovery Section
        recovery_frame = tk.LabelFrame(main_container, text="Fault Recovery Status")
        recovery_frame.pack(fill="x", pady=5, padx=5)

        recovery_info_frame = tk.Frame(recovery_frame)
        recovery_info_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(recovery_info_frame, text="Status:", width=8, anchor="e").pack(side="left", padx=5)
        tk.Entry(recovery_info_frame, textvariable=self.recovery_status, width=40, state="readonly").pack(side="left",
                                                                                                          padx=5,
                                                                                                          fill="x",
                                                                                                          expand=True)
        tk.Label(recovery_info_frame, text="Countdown:", width=10, anchor="e").pack(side="left", padx=5)
        tk.Entry(recovery_info_frame, textvariable=self.recovery_countdown, width=15, state="readonly").pack(
            side="left", padx=5)

        # ✅ Status Frame
        status_frame = tk.Frame(main_container)
        status_frame.pack(fill="x", pady=5)

        lights_frame = tk.Frame(status_frame)
        lights_frame.pack()
        self.create_status_lights(lights_frame)

        message_frame = tk.LabelFrame(status_frame, text="Status Message")
        message_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(message_frame, textvariable=self.status_message).pack(pady=5)

        # ✅ Timer Display
        timer_frame = tk.LabelFrame(main_container, text="Direction Timer")
        timer_frame.pack(fill="x", pady=5)

        timer_info_frame = tk.Frame(timer_frame)
        timer_info_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(timer_info_frame, text="Current Direction:", width=15, anchor="e").pack(side="left", padx=5)
        tk.Entry(timer_info_frame, textvariable=self.current_direction, state="readonly", width=10).pack(side="left",
                                                                                                         padx=5)
        tk.Label(timer_info_frame, text="Time Remaining:", width=15, anchor="e").pack(side="left", padx=5)
        tk.Entry(timer_info_frame, textvariable=self.direction_timer, state="readonly", width=10).pack(side="left",
                                                                                                       padx=5)

        self.progress_bar = ttk.Progressbar(timer_frame, orient="horizontal", length=300, mode="determinate",
                                            variable=self.direction_progress)
        self.progress_bar.pack(fill="x", padx=10, pady=5)

    def create_param_row(self, parent, label_text, variable, unit, readonly=False):
        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=2)

        tk.Label(frame, text=label_text, width=15, anchor="e").pack(side="left", padx=2)
        tk.Entry(frame, textvariable=variable, width=8,
                 state="readonly" if readonly else "normal").pack(side="left", padx=2)
        tk.Label(frame, text=unit, width=4, anchor="w").pack(side="left")

    def create_status_lights(self, parent):
        self.canvas_red = tk.Canvas(parent, width=30, height=30)
        self.canvas_yellow = tk.Canvas(parent, width=30, height=30)
        self.canvas_green = tk.Canvas(parent, width=30, height=30)

        self.canvas_red.pack(side="left", padx=5)
        self.canvas_yellow.pack(side="left", padx=5)
        self.canvas_green.pack(side="left", padx=5)

        # Add labels for lights
        tk.Label(parent, text="Fault").pack(side="left", padx=5)
        tk.Label(parent, text="Warning").pack(side="left", padx=5)
        tk.Label(parent, text="OK").pack(side="left", padx=5)

        self.update_status_lights("ready")

    def update_status_lights(self, status):
        """Updates status lights based on system state"""
        # Clear all lights
        for canvas in [self.canvas_red, self.canvas_yellow, self.canvas_green]:
            canvas.delete("all")
            canvas.create_oval(5, 5, 25, 25, fill="grey")

        if status == "running":
            self.canvas_green.delete("all")
            self.canvas_green.create_oval(5, 5, 25, 25, fill="green")
            self.status_message.set("Motor is Running")
        elif status == "warning":
            self.canvas_yellow.delete("all")
            self.canvas_yellow.create_oval(5, 5, 25, 25, fill="yellow")
            self.status_message.set("Warning: Check Parameters")
        elif status == "fault":
            self.canvas_red.delete("all")
            self.canvas_red.create_oval(5, 5, 25, 25, fill="red")
            self.status_message.set("Fault Detected: Motor Stopped")
        elif status == "stopped":
            self.canvas_red.delete("all")
            self.canvas_red.create_oval(5, 5, 25, 25, fill="red")
            self.status_message.set("System Stopped")
        elif status == "recovering":
            self.canvas_yellow.delete("all")
            self.canvas_yellow.create_oval(5, 5, 25, 25, fill="yellow")
            self.canvas_red.delete("all")
            self.canvas_red.create_oval(5, 5, 25, 25, fill="red")
            self.status_message.set("Fault Recovery in Progress")
        elif status == "completed":
            # Flash all lights green to indicate successful completion
            for canvas in [self.canvas_red, self.canvas_yellow, self.canvas_green]:
                canvas.delete("all")
                canvas.create_oval(5, 5, 25, 25, fill="green")
            self.status_message.set("Target Cycles Completed Successfully")
        else:  # ready
            self.canvas_green.delete("all")
            self.canvas_green.create_oval(5, 5, 25, 25, fill="green")
            self.status_message.set("System Ready")

    def update_fault_warning_displays(self, faults, warnings, faults_reg=0, faults2_reg=0, warnings_reg=0,
                                      warnings2_reg=0):
        """Updates the fault and warning displays with current information"""
        # Update register values
        self.fault_reg_value.set(f"0x{faults_reg:04X}")  # Hexadecimal format for easier bit reading
        self.fault2_reg_value.set(f"0x{faults2_reg:04X}")
        self.warning_reg_value.set(f"0x{warnings_reg:04X}")
        self.warning2_reg_value.set(f"0x{warnings2_reg:04X}")

        # Update fault display
        self.fault_display.config(state="normal")
        self.fault_display.delete(1.0, tk.END)
        if faults:
            for fault in faults:
                self.fault_display.insert(tk.END, f"• {fault}\n")

            # Add binary representation of the registers to help with debugging
            self.fault_display.insert(tk.END, "\nRegister values (binary):\n")
            self.fault_display.insert(tk.END, f"Fault: {bin(faults_reg)[2:].zfill(16)}\n")
            self.fault_display.insert(tk.END, f"Fault2: {bin(faults2_reg)[2:].zfill(16)}\n")
        else:
            self.fault_display.insert(tk.END, "No active faults")
        self.fault_display.config(state="disabled")

        # Update warning display
        self.warning_display.config(state="normal")
        self.warning_display.delete(1.0, tk.END)
        if warnings:
            for warning in warnings:
                self.warning_display.insert(tk.END, f"• {warning}\n")

            # Add binary representation of the registers to help with debugging
            self.warning_display.insert(tk.END, "\nRegister values (binary):\n")
            self.warning_display.insert(tk.END, f"Warning: {bin(warnings_reg)[2:].zfill(16)}\n")
            self.warning_display.insert(tk.END, f"Warning2: {bin(warnings2_reg)[2:].zfill(16)}\n")
        else:
            self.warning_display.insert(tk.END, "No active warnings")
        self.warning_display.config(state="disabled")

        # Update status lights based on faults and warnings
        if faults:
            self.update_status_lights("fault")
        elif warnings:
            self.update_status_lights("warning")
        elif self.running:
            self.update_status_lights("running")
        else:
            self.update_status_lights("ready")

    def handle_recovery_status(self, status, value):
        """Callback for handling recovery status updates"""
        if status == "recovery_started":
            self.recovery_status.set(f"Recovery started: {value}")
            self.update_status_lights("recovering")
        elif status == "recovery_countdown":
            self.recovery_countdown.set(f"Next attempt: {value}")
        elif status == "recovery_waiting":
            self.recovery_status.set(f"Status: {value}")
            self.recovery_countdown.set("")
        elif status == "recovery_successful":
            self.recovery_status.set("Recovery successful!")
            self.recovery_countdown.set("")
            self.update_status_lights("running")
        elif status == "recovery_stopped":
            self.recovery_status.set("Recovery stopped")
            self.recovery_countdown.set("")
            self.update_status_lights("fault")
        elif status == "recovery_stage_change":
            self.recovery_status.set(f"Moving to {value}")
        elif status == "recovery_error":
            self.recovery_status.set(f"Error: {value}")
        elif status == "recovery_failed":
            self.recovery_status.set("Recovery failed – manual reset required")
            self.recovery_countdown.set("")
            self.update_status_lights("fault")

    async def async_check_faults_warnings(self):
        """Asynchronously check for faults and warnings"""
        if not self.motor_controller:
            return [], [], 0, 0, 0, 0

        try:
            faults, faults_reg, faults2_reg = await self.motor_controller.check_faults()
            warnings, warnings_reg, warnings2_reg = await self.motor_controller.check_warnings()
            return faults, warnings, faults_reg, faults2_reg, warnings_reg, warnings2_reg
        except Exception as e:
            logging.error(f"Error checking faults/warnings: {e}")
            return [], [], 0, 0, 0, 0

    async def async_update_parameters(self):
        """Asynchronously updates all GUI parameters with current motor values"""
        check_interval = 1.0  # Check every second

        while True:
            try:
                if self.motor_controller:
                    # Check for faults and warnings, even when not running
                    faults, warnings, faults_reg, faults2_reg, warnings_reg, warnings2_reg = await self.async_check_faults_warnings()
                    self.root.after(0, lambda: self.update_fault_warning_displays(
                        faults, warnings, faults_reg, faults2_reg, warnings_reg, warnings2_reg))

                    if self.running:
                        try:
                            # Update motor parameters
                            motor_rpm = await self.motor_controller.read_motor_data("motor_rpm")
                            motor_current = await self.motor_controller.read_motor_data("motor_current")
                            motor_temp = await self.motor_controller.read_motor_data("motor_temp")
                            controller_temp = await self.motor_controller.read_motor_data("controller_temp")
                            battery_voltage = await self.motor_controller.read_motor_data("battery_voltage")
                            battery_current = await self.motor_controller.read_motor_data("battery_current")

                            # Update GUI elements from the main thread
                            self.root.after(0, lambda: self.update_ui_values(
                                motor_rpm, motor_current, motor_temp, controller_temp,
                                battery_voltage, battery_current
                            ))

                            # Update cycle count
                            current_count = self.motor_controller.get_last_cycle_count("No_of_cycles.txt")
                            self.root.after(0, lambda: self.current_cycle.set(str(current_count)))

                        except Exception as e:
                            logging.error(f"Error updating motor parameters: {e}")
            except Exception as e:
                logging.error(f"Error in parameter update loop: {e}")

            await asyncio.sleep(check_interval)

    def update_ui_values(self, rpm, current, m_temp, c_temp, voltage, b_current):
        """Update UI values from the main thread"""
        self.motor_rpm.set(str(rpm or 0))
        self.motor_current.set(str(current or 0))
        self.motor_temp.set(str(m_temp or 0))
        self.controller_temp.set(str(c_temp or 0))
        self.battery_voltage.set(f"{voltage or 0:.1f}")
        self.battery_current.set(str(b_current or 0))

    def update_timer_display(self, direction, elapsed_time, total_time):
        """Updates the timer display with the current direction and remaining time"""
        if direction == "forward":
            self.current_direction.set("Forward")
        elif direction == "reverse":
            self.current_direction.set("Reverse")
        else:
            self.current_direction.set("None")
            self.direction_timer.set("0.0")
            self.direction_progress.set(0)
            return

        remaining_time = max(0, total_time - elapsed_time)
        self.direction_timer.set(f"{remaining_time:.1f}")

        # Update progress bar (0-100%)
        progress_percent = min(100, (elapsed_time / total_time) * 100)
        self.direction_progress.set(progress_percent)

    def start_test(self):
        """Handles the start button click"""
        if not self.running and self.motor_controller:
            try:
                target_cycles = int(self.target_cycles.get())
                if target_cycles == 0 or target_cycles < -1:
                    messagebox.showerror("Error",
                                         "Please enter -1 for continuous mode or a positive number for specific cycles")
                    return

                # Collect parameters from GUI
                params = {
                    "target_rpm": float(self.target_rpm.get()),
                    "forward_torque": float(self.forward_torque.get()),
                    "reverse_torque": float(self.reverse_torque.get()),
                    "forward_duration": float(self.forward_duration.get()),
                    "reverse_duration": float(self.reverse_duration.get()),
                    "max_motor_current": float(self.max_motor_current.get()),
                    "max_brake_current": float(self.max_brake_current.get())
                }

                self.running = True
                self.update_status_lights("running")

                # Update status message based on mode
                if target_cycles == -1:
                    self.status_message.set("Running in continuous mode")
                else:
                    self.status_message.set("Running test cycle")

                self.start_button.config(state="disabled")

                # Run the test in the asyncio loop
                self.loop.call_soon_threadsafe(lambda: self.async_run_test(params, target_cycles))

            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for all parameters")
                self.stop_test()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start test: {str(e)}")
                self.stop_test()

    def async_run_test(self, params, target_cycles):
        """Runs the test in the asyncio event loop"""

        async def run_test():
            try:
                # Create callbacks
                def fault_callback(faults, warnings, faults_reg=0, faults2_reg=0, warnings_reg=0, warnings2_reg=0):
                    if isinstance(faults, str) and faults.startswith("recovery_"):
                        self.root.after(0, lambda: self.handle_recovery_status(faults, warnings))
                    else:
                        self.root.after(0, lambda: self.update_fault_warning_displays(
                            faults, warnings, faults_reg, faults2_reg, warnings_reg, warnings2_reg))

                def timer_callback(direction, elapsed_time, total_time):
                    self.root.after(0, lambda: self.update_timer_display(direction, elapsed_time, total_time))

                # Start the motor test
                final_cycle = await self.motor_controller.start_test(
                    params=params,
                    cycle_count_target=target_cycles,
                    fault_check_callback=fault_callback,
                    timer_callback=timer_callback
                )

                # Handle completion
                if target_cycles != -1 and self.running:
                    self.root.after(0, lambda: self.handle_test_completion("completed"))

            except asyncio.CancelledError:
                logging.info("Test task cancelled")
            except Exception as e:
                logging.error(f"Error in test task: {e}")
                self.root.after(0, lambda: self.handle_test_completion("error"))

        # Create and store the task
        self.test_task = asyncio.create_task(run_test())

    def handle_test_completion(self, status):
        """Handles test completion and updates UI accordingly"""
        self.running = False
        self.start_button.config(state="normal")

        if status == "completed" and self.target_cycles.get() != "-1":
            self.update_status_lights("completed")
            self.status_message.set("Test Completed Successfully")
            messagebox.showinfo("Success", "Target cycles completed successfully!")
        else:
            self.update_status_lights("stopped")
            self.status_message.set("Test Stopped")

    def stop_test(self):
        """Handles the stop button click"""
        self.running = False
        self.update_status_lights("stopped")
        self.start_button.config(state="normal")
        # Reset the timer display
        self.update_timer_display("none", 0, 1)

        # Cancel the test task if it exists
        if self.test_task and not self.test_task.done():
            self.test_task.cancel()

        # Stop the test in the asyncio loop
        if self.motor_controller:
            self.loop.call_soon_threadsafe(self.async_stop_test)

        # Reset recovery status
        self.recovery_status.set("")
        self.recovery_countdown.set("")

    def async_stop_test(self):
        """Stops the test in the asyncio event loop"""

        async def stop():
            try:
                await self.motor_controller.stop_test()
            except Exception as e:
                logging.error(f"Error stopping test: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error stopping test: {str(e)}"))

        asyncio.create_task(stop())

    def update_parameters(self):
        """Updates all GUI parameters with current motor values"""
        if self.running and self.motor_controller:
            self.loop.call_soon_threadsafe(self.async_update_params_once)

        # Schedule the next update
        self.root.after(1000, self.update_parameters)

    def async_update_params_once(self):
        """Updates parameters once asynchronously"""

        async def update():
            try:
                motor_rpm = await self.motor_controller.read_motor_data("motor_rpm")
                motor_current = await self.motor_controller.read_motor_data("motor_current")
                motor_temp = await self.motor_controller.read_motor_data("motor_temp")
                controller_temp = await self.motor_controller.read_motor_data("controller_temp")
                battery_voltage = await self.motor_controller.read_motor_data("battery_voltage")
                battery_current = await self.motor_controller.read_motor_data("battery_current")

                # Update GUI elements from the main thread
                self.root.after(0, lambda: self.update_ui_values(
                    motor_rpm, motor_current, motor_temp, controller_temp,
                    battery_voltage, battery_current
                ))

                # Update cycle count
                current_count = self.motor_controller.get_last_cycle_count("No_of_cycles.txt")
                self.root.after(0, lambda: self.current_cycle.set(str(current_count)))

            except Exception as e:
                logging.error(f"Error in manual parameter update: {e}")

        asyncio.create_task(update())


def main():
    # Setup logging
    try:
        from src.config import LOGGING_CONFIG
        log_dir = Path(LOGGING_CONFIG["filename"]).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOGGING_CONFIG["filename"]),
                logging.StreamHandler()
            ]
        )
    except Exception as e:
        # Fallback logging setup
        logging.basicConfig(level=logging.INFO)
        logging.warning(f"Could not setup logging from config: {e}")

    root = tk.Tk()
    app = OneWayClutchTesterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()