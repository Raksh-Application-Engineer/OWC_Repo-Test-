#!/usr/bin/env python3
"""
Production-Ready Installation Script
Handles Python detection, path issues, and user-friendly setup
"""

import os
import sys
import subprocess
import venv
import platform
import shutil
from pathlib import Path


def print_header():
    """Print installation header"""
    print("=" * 70)
    print("          ONE-WAY CLUTCH TESTER - INSTALLATION")
    print("=" * 70)
    print()


def print_status(message, status="INFO"):
    """Print formatted status message"""
    symbols = {"INFO": "[INFO]", "ERROR": "[ERROR]", "SUCCESS": "[SUCCESS]", "WARNING": "[WARNING]"}
    print(f"{symbols.get(status, '[INFO]')} {message}")


def check_python_installation():
    """Check and validate Python installation"""
    print_status("Checking Python installation...")

    # List of possible Python commands to try
    python_commands = ['python', 'python3', 'py']
    working_python = None
    python_version = None

    for cmd in python_commands:
        try:
            result = subprocess.run([cmd, '--version'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_output = result.stdout.strip()
                print_status(f"Found Python: {version_output}")

                # Extract version number
                version_parts = version_output.split()[1].split('.')
                major, minor = int(version_parts[0]), int(version_parts[1])

                if major >= 3 and minor >= 7:
                    working_python = cmd
                    python_version = f"{major}.{minor}"
                    print_status(f"Python {python_version} is compatible", "SUCCESS")
                    break
                else:
                    print_status(f"Python {major}.{minor} is too old (need 3.7+)", "WARNING")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            continue

    return working_python, python_version


def find_python_executable():
    """Comprehensive Python executable detection for Windows"""
    if platform.system().lower() != 'windows':
        return None

    print_status("Searching for Python installation on Windows...")

    # Common Python installation paths
    search_paths = [
        Path(f"C:/Users/{os.getenv('USERNAME')}/AppData/Local/Programs/Python"),
        Path("C:/Program Files/Python*"),
        Path("C:/Program Files (x86)/Python*"),
        Path(f"C:/Users/{os.getenv('USERNAME')}/AppData/Local/Microsoft/WindowsApps"),
        Path("C:/Python*")
    ]

    python_executables = []

    for search_path in search_paths:
        try:
            if '*' in str(search_path):
                # Handle wildcard paths
                parent = Path(str(search_path).split('*')[0])
                if parent.exists():
                    for path in parent.glob(str(search_path).split('/')[-1]):
                        python_exe = path / "python.exe"
                        if python_exe.exists():
                            python_executables.append(python_exe)
            else:
                if search_path.exists():
                    for python_exe in search_path.rglob("python.exe"):
                        python_executables.append(python_exe)
        except Exception as e:
            continue

    # Test each found executable
    for exe_path in python_executables:
        try:
            result = subprocess.run([str(exe_path), '--version'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                print_status(f"Found: {exe_path} - {version}")
                return str(exe_path)
        except:
            continue

    return None


def install_python_windows():
    """Guide user through Python installation on Windows"""
    print_status("Python not found. Installation required.", "ERROR")
    print()
    print("PYTHON INSTALLATION REQUIRED")
    print("-" * 40)
    print("Please install Python from one of these sources:")
    print()
    print("Option 1 (Recommended): Microsoft Store")
    print("  1. Press Win + S, search 'Microsoft Store'")
    print("  2. Search for 'Python 3.12'")
    print("  3. Click 'Install'")
    print()
    print("Option 2: Official Python Website")
    print("  1. Visit: https://www.python.org/downloads/")
    print("  2. Download Python 3.12+ for Windows")
    print("  3. Run installer with 'Add to PATH' checked")
    print()
    print("After installation:")
    print("  1. Restart this command prompt")
    print("  2. Run: python install.py")
    print()

    response = input("Press Enter to continue or 'q' to quit: ").lower()
    if response == 'q':
        sys.exit(1)

    # Try to open Microsoft Store (Windows 10+)
    try:
        subprocess.run(['start', 'ms-windows-store://pdp/?ProductId=9NRWMJP3717K'],
                       shell=True, check=False)
    except:
        pass


def post_clone_setup():
    """Main setup function with comprehensive error handling"""
    print_header()

    project_root = Path(__file__).parent.absolute()
    print_status(f"Project location: {project_root}")

    # Check Python installation
    python_cmd, python_version = check_python_installation()

    if not python_cmd:
        # Try to find Python executable directly (Windows)
        python_exe = find_python_executable()
        if python_exe:
            python_cmd = python_exe
            print_status(f"Found Python executable: {python_exe}", "SUCCESS")
        else:
            if platform.system().lower() == 'windows':
                install_python_windows()
                return False
            else:
                print_status("Python 3.7+ required but not found", "ERROR")
                print("Please install Python 3.7+ and try again")
                return False

    # Validate project structure
    if not validate_project_structure(project_root):
        return False

    # Create virtual environment
    venv_path = project_root / "venv"
    if not create_virtual_environment(python_cmd, venv_path):
        return False

    # Install dependencies
    if not install_dependencies(python_cmd, project_root, venv_path):
        return False

    # Create launcher scripts
    if not create_launcher_scripts(project_root, venv_path, python_cmd):
        return False

    # Create desktop shortcuts
    create_desktop_shortcuts(project_root)

    # Setup permissions (Linux)
    setup_permissions()

    print()
    print_status("INSTALLATION COMPLETED SUCCESSFULLY!", "SUCCESS")
    print()
    print("Next Steps:")
    print("1. Look for 'One-Way Clutch Tester' shortcut on your desktop")
    print("2. Double-click the shortcut to launch the application")
    if platform.system().lower() == 'linux':
        print("3. On Linux: Log out and back in if this is first setup")
    print()
    return True


def validate_project_structure(project_root):
    """Validate project structure and create missing files"""
    print_status("Validating project structure...")

    required_files = {
        "src/gui.py": "Main GUI application",
        "src/motor_controller.py": "Motor control logic",
        "src/config.py": "Configuration file",
        "requirements.txt": "Dependencies list"
    }

    missing_files = []
    for file_path, description in required_files.items():
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(f"{file_path} ({description})")

    if missing_files:
        print_status("Missing required files:", "ERROR")
        for file in missing_files:
            print(f"  - {file}")
        return False

    # Create __init__.py if missing
    init_file = project_root / "src" / "__init__.py"
    if not init_file.exists():
        init_file.touch()
        print_status("Created src/__init__.py")

    # Create assets directory if missing
    assets_dir = project_root / "assets"
    assets_dir.mkdir(exist_ok=True)

    print_status("Project structure validated", "SUCCESS")
    return True


def create_virtual_environment(python_cmd, venv_path):
    """Create virtual environment with proper Python command"""
    if venv_path.exists():
        print_status("Virtual environment already exists")
        return True

    try:
        print_status("Creating virtual environment...")
        subprocess.run([python_cmd, "-m", "venv", str(venv_path)],
                       check=True, capture_output=True)
        print_status("Virtual environment created successfully", "SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to create virtual environment: {e}", "ERROR")
        print("Try installing Python with 'Add to PATH' option enabled")
        return False


def install_dependencies(python_cmd, project_root, venv_path):
    """Install dependencies with better error handling"""
    system = platform.system().lower()

    # Get correct pip path
    if system == "windows":
        pip_exe = venv_path / "Scripts" / "pip.exe"
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        pip_exe = venv_path / "bin" / "pip"
        python_exe = venv_path / "bin" / "python"

    requirements = project_root / "requirements.txt"

    if not requirements.exists():
        print_status("requirements.txt not found!", "ERROR")
        return False

    try:
        print_status("Upgrading pip...")
        subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
                       check=True, capture_output=True, text=True)

        print_status("Installing project dependencies...")
        result = subprocess.run([str(pip_exe), "install", "-r", str(requirements)],
                                check=True, capture_output=True, text=True)

        print_status("Dependencies installed successfully", "SUCCESS")
        return True

    except subprocess.CalledProcessError as e:
        print_status("Dependency installation failed", "ERROR")
        print(f"Error: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")

        # Try alternative installation method
        print_status("Trying alternative installation method...")
        try:
            subprocess.run([python_cmd, "-m", "pip", "install", "-r", str(requirements)],
                           check=True)
            print_status("Alternative installation successful", "SUCCESS")
            return True
        except:
            print_status("All installation methods failed", "ERROR")
            return False


def create_launcher_scripts(project_root, venv_path, python_cmd):
    """Create robust launcher scripts"""
    system = platform.system().lower()

    try:
        if system == "windows":
            create_windows_launcher(project_root, venv_path)
        else:
            create_linux_launcher(project_root, venv_path)
        return True
    except Exception as e:
        print_status(f"Failed to create launcher: {e}", "ERROR")
        return False


def create_windows_launcher(project_root, venv_path):
    """Create robust Windows launcher"""
    launcher_content = f'''@echo off
title One-Way Clutch Tester
color 0A

echo =====================================
echo   ONE-WAY CLUTCH TESTER LAUNCHER
echo =====================================
echo.

cd /d "{project_root}"

echo Activating virtual environment...
call "{venv_path}\\Scripts\\activate.bat"

echo Starting application...
python src\\gui.py

if errorlevel 1 (
    echo.
    echo =====================================
    echo   APPLICATION ERROR DETECTED
    echo =====================================
    echo.
    echo Check the following:
    echo 1. Motor controller is connected
    echo 2. COM port is available
    echo 3. Check log files for details
    echo.
    echo Log location: %USERPROFILE%\\Documents\\OneWayClutchTester\\logs\\
    echo.
    pause
) else (
    echo.
    echo Application closed normally.
    timeout /t 3 /nobreak >nul
)
'''

    launcher_path = project_root / "OneWayClutchTester.bat"
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    print_status(f"Created Windows launcher: {launcher_path.name}")


def create_linux_launcher(project_root, venv_path):
    """Create robust Linux launcher"""
    launcher_content = f'''#!/bin/bash

echo "======================================"
echo "   ONE-WAY CLUTCH TESTER LAUNCHER"
echo "======================================"
echo

cd "{project_root}"

echo "Activating virtual environment..."
source "{venv_path}/bin/activate"

echo "Starting application..."
python src/gui.py

exit_code=$?
echo

if [ $exit_code -ne 0 ]; then
    echo "======================================"
    echo "   APPLICATION ERROR DETECTED"
    echo "======================================"
    echo
    echo "Check the following:"
    echo "1. Motor controller is connected"
    echo "2. Serial port permissions"
    echo "3. Check log files for details"
    echo
    echo "Log location: ~/one_way_clutch_data/logs/"
    echo
    read -p "Press Enter to close..."
else
    echo "Application closed normally."
    sleep 2
fi
'''

    launcher_path = project_root / "OneWayClutchTester.sh"
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    os.chmod(launcher_path, 0o755)
    print_status(f"Created Linux launcher: {launcher_path.name}")


def create_desktop_shortcuts(project_root):
    """Create desktop shortcuts with better error handling"""
    system = platform.system().lower()

    try:
        if system == "windows":
            create_windows_shortcut(project_root)
        else:
            create_linux_shortcut(project_root)
    except Exception as e:
        print_status(f"Could not create desktop shortcut: {e}", "WARNING")
        print_status("You can manually run the launcher script", "INFO")


def create_windows_shortcut(project_root):
    """Create Windows desktop shortcut with fallback methods"""
    try:
        # Method 1: Try with winshell
        try:
            import winshell
            from win32com.client import Dispatch
        except ImportError:
            print_status("Installing shortcut creation tools...")
            subprocess.run([sys.executable, "-m", "pip", "install", "winshell", "pywin32"],
                           check=True, capture_output=True)
            import winshell
            from win32com.client import Dispatch

        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, "One-Way Clutch Tester.lnk")
        launcher_path = project_root / "OneWayClutchTester.bat"

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = str(launcher_path)
        shortcut.WorkingDirectory = str(project_root)
        shortcut.Description = "One-Way Clutch Tester Application"
        shortcut.save()

        print_status(f"Desktop shortcut created successfully", "SUCCESS")

    except Exception as e:
        # Fallback: Create a simple batch file on desktop
        try:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                desktop = Path.home() / "OneDrive" / "Desktop"  # OneDrive desktop

            if desktop.exists():
                shortcut_content = f'@echo off\ncd /d "{project_root}"\ncall OneWayClutchTester.bat'
                shortcut_path = desktop / "One-Way Clutch Tester.bat"
                with open(shortcut_path, 'w') as f:
                    f.write(shortcut_content)
                print_status("Created fallback desktop shortcut", "SUCCESS")
            else:
                print_status("Could not find desktop folder", "WARNING")
        except Exception as fallback_error:
            print_status(f"Shortcut creation failed: {fallback_error}", "WARNING")


def create_linux_shortcut(project_root):
    """Create Linux desktop shortcut"""
    desktop_locations = [
        Path.home() / "Desktop",
        Path.home() / ".local/share/applications"
    ]

    created = False
    for desktop_path in desktop_locations:
        try:
            desktop_path.mkdir(parents=True, exist_ok=True)

            shortcut_path = desktop_path / "one-way-clutch-tester.desktop"
            launcher_path = project_root / "OneWayClutchTester.sh"
            icon_path = project_root / "assets" / "download.png"

            desktop_entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=One-Way Clutch Tester
Comment=Sprag Clutch Testing Application
Exec={launcher_path}
Icon={icon_path if icon_path.exists() else 'applications-engineering'}
Terminal=false
Categories=Engineering;Development;
StartupNotify=true
Path={project_root}
"""

            with open(shortcut_path, 'w') as f:
                f.write(desktop_entry)
            os.chmod(shortcut_path, 0o755)

            print_status(f"Desktop shortcut created: {shortcut_path}")
            created = True
            break

        except Exception as e:
            continue

    if not created:
        print_status("Could not create desktop shortcut", "WARNING")


def setup_permissions():
    """Setup serial port permissions on Linux"""
    system = platform.system().lower()
    if system == "linux":
        try:
            username = os.getenv('USER')
            if username:
                # Check if already in dialout group
                result = subprocess.run(['groups', username],
                                        capture_output=True, text=True)
                if 'dialout' not in result.stdout:
                    print_status("Setting up serial port permissions...")
                    subprocess.run(['sudo', 'usermod', '-a', '-G', 'dialout', username],
                                   check=True)
                    print_status("Added user to dialout group", "SUCCESS")
                    print_status("Please log out and back in for changes to take effect", "WARNING")
                else:
                    print_status("Serial permissions already configured", "SUCCESS")
        except Exception as e:
            print_status(f"Could not setup serial permissions: {e}", "WARNING")
            print("You may need to manually add user to dialout group")


def create_troubleshooting_guide(project_root):
    """Create a troubleshooting guide file"""
    guide_content = """# One-Way Clutch Tester - Troubleshooting Guide

## Common Issues and Solutions

### 1. "Python was not found"
**Windows**:
- Install Python from Microsoft Store or python.org
- Ensure "Add to PATH" is checked during installation
- Restart command prompt after installation

**Linux**:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. "Permission denied" (Linux)
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### 3. "No serial ports found"
- Check USB cable connection
- Verify motor controller is powered
- Try different USB port

### 4. Application won't start
- Re-run: python install.py
- Check log files in data directory
- Verify all cables are connected

## Manual Launch (if shortcuts fail)
**Windows**: Double-click OneWayClutchTester.bat
**Linux**: Run ./OneWayClutchTester.sh

## Log Locations
**Windows**: Documents/OneWayClutchTester/logs/
**Linux**: ~/one_way_clutch_data/logs/

For more help, check the full README.md file.
"""

    try:
        guide_path = project_root / "TROUBLESHOOTING.md"
        with open(guide_path, 'w') as f:
            f.write(guide_content)
        print_status("Created troubleshooting guide")
    except Exception as e:
        print_status(f"Could not create troubleshooting guide: {e}", "WARNING")


def main():
    """Main entry point with error handling"""
    try:
        success = post_clone_setup()

        # Create troubleshooting guide
        project_root = Path(__file__).parent.absolute()
        create_troubleshooting_guide(project_root)

        if success:
            print()
            input("Press Enter to close this window...")
            return 0
        else:
            print()
            input("Press Enter to close this window...")
            return 1

    except KeyboardInterrupt:
        print("\nInstallation cancelled by user")
        return 1
    except Exception as e:
        print_status(f"Unexpected error during installation: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())