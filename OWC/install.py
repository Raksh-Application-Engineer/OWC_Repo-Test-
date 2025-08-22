#!/usr/bin/env python3
"""
Post-clone installation script - Fixed for deployment readiness
Run this after cloning the repository
"""

import os
import sys
import subprocess
import venv
import platform
from pathlib import Path


def print_status(message):
    """Print status message with formatting"""
    print(f"[SETUP] {message}")


def run_command(cmd, check=True, capture_output=False):
    """Run command with proper error handling"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, check=check,
                                    capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=check)
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e}")
        if capture_output:
            print(f"Error output: {e.stderr}")
        return False


def post_clone_setup():
    """Main setup function after git clone"""
    project_root = Path(__file__).parent.absolute()
    print_status(f"Setting up One-Way Clutch Tester in: {project_root}")

    # Validate project structure
    if not validate_project_structure(project_root):
        print("ERROR: Project structure validation failed!")
        return False

    # Create virtual environment
    venv_path = project_root / "venv"
    if not create_virtual_environment(venv_path):
        return False

    # Install dependencies
    if not install_dependencies(project_root, venv_path):
        return False

    # Create launcher scripts
    if not create_launcher_scripts(project_root, venv_path):
        return False

    # Create desktop shortcuts
    if not create_desktop_shortcuts(project_root):
        return False

    # Setup permissions (Linux)
    setup_permissions()

    print_status("Setup completed successfully!")
    print_status("You can now double-click the desktop shortcut to run the application.")
    return True


def validate_project_structure(project_root):
    """Validate that all required files exist"""
    required_files = [
        "src/gui.py",
        "src/motor_controller.py",
        "src/config.py",
        "requirements.txt"
    ]

    missing_files = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"ERROR: Missing required files: {missing_files}")
        return False

    # Create __init__.py if missing
    init_file = project_root / "src" / "__init__.py"
    if not init_file.exists():
        init_file.touch()
        print_status("Created missing src/__init__.py")

    return True


def create_virtual_environment(venv_path):
    """Create virtual environment with error handling"""
    if venv_path.exists():
        print_status("Virtual environment already exists, skipping creation")
        return True

    try:
        print_status("Creating virtual environment...")
        venv.create(venv_path, with_pip=True)
        print_status("Virtual environment created successfully")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create virtual environment: {e}")
        return False


def install_dependencies(project_root, venv_path):
    """Install required packages with better error handling"""
    system = platform.system().lower()

    # Determine pip executable path
    if system == "windows":
        pip_exe = venv_path / "Scripts" / "pip.exe"
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        pip_exe = venv_path / "bin" / "pip"
        python_exe = venv_path / "bin" / "python"

    requirements = project_root / "requirements.txt"

    if not requirements.exists():
        print("ERROR: requirements.txt not found!")
        return False

    try:
        print_status("Upgrading pip...")
        subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
                       check=True, capture_output=True)

        print_status("Installing dependencies...")
        subprocess.run([str(pip_exe), "install", "-r", str(requirements)],
                       check=True, capture_output=True)

        print_status("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install dependencies: {e}")
        return False


def create_launcher_scripts(project_root, venv_path):
    """Create OS-specific launcher scripts"""
    system = platform.system().lower()

    try:
        if system == "windows":
            create_windows_launcher(project_root, venv_path)
        else:
            create_linux_launcher(project_root, venv_path)
        return True
    except Exception as e:
        print(f"ERROR: Failed to create launcher scripts: {e}")
        return False


def create_windows_launcher(project_root, venv_path):
    """Create Windows batch launcher"""
    launcher_content = f'''@echo off
cd /d "{project_root}"
call "{venv_path}\\Scripts\\activate.bat"
python src\\gui.py
if errorlevel 1 (
    echo.
    echo Application encountered an error. Press any key to close...
    pause >nul
) else (
    echo.
    echo Application closed normally. Press any key to close...
    pause >nul
)
'''
    launcher_path = project_root / "OneWayClutchTester.bat"
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    print_status(f"Created Windows launcher: {launcher_path}")


def create_linux_launcher(project_root, venv_path):
    """Create Linux shell launcher"""
    launcher_content = f'''#!/bin/bash
cd "{project_root}"
source "{venv_path}/bin/activate"

echo "Starting One-Way Clutch Tester..."
python src/gui.py

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Application encountered an error (exit code: $exit_code)"
    read -p "Press Enter to close..."
else
    echo "Application closed normally"
fi
'''
    launcher_path = project_root / "OneWayClutchTester.sh"
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    os.chmod(launcher_path, 0o755)
    print_status(f"Created Linux launcher: {launcher_path}")


def create_desktop_shortcuts(project_root):
    """Create desktop shortcuts with error handling"""
    system = platform.system().lower()

    try:
        if system == "windows":
            return create_windows_shortcut(project_root)
        else:
            return create_linux_shortcut(project_root)
    except Exception as e:
        print(f"WARNING: Could not create desktop shortcut: {e}")
        return True  # Don't fail setup for shortcut issues


def create_windows_shortcut(project_root):
    """Create Windows desktop shortcut"""
    try:
        # Try to install required packages first
        try:
            import winshell
            from win32com.client import Dispatch
        except ImportError:
            print_status("Installing Windows shortcut dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "winshell", "pywin32"],
                           check=True)
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

        # Try to set icon
        icon_path = project_root / "assets" / "download.png"
        if icon_path.exists():
            shortcut.IconLocation = str(icon_path)

        shortcut.save()
        print_status(f"Desktop shortcut created: {shortcut_path}")
        return True
    except Exception as e:
        print(f"WARNING: Failed to create Windows shortcut: {e}")
        return True


def create_linux_shortcut(project_root):
    """Create Linux desktop shortcut"""
    # Try multiple desktop locations
    desktop_locations = [
        Path.home() / "Desktop",
        Path.home() / ".local/share/applications"
    ]

    for desktop_path in desktop_locations:
        if desktop_path.exists() or desktop_path.name == "applications":
            desktop_path.mkdir(parents=True, exist_ok=True)
            break
    else:
        desktop_path = Path.home() / "Desktop"
        desktop_path.mkdir(exist_ok=True)

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
"""

    with open(shortcut_path, 'w') as f:
        f.write(desktop_entry)

    os.chmod(shortcut_path, 0o755)
    print_status(f"Desktop shortcut created: {shortcut_path}")
    return True


def setup_permissions():
    """Setup serial port permissions on Linux"""
    system = platform.system().lower()
    if system == "linux":
        try:
            username = os.getenv('USER')
            if username:
                result = subprocess.run(['groups', username],
                                        capture_output=True, text=True)
                if 'dialout' not in result.stdout:
                    print_status("Adding user to dialout group for serial access...")
                    subprocess.run(['sudo', 'usermod', '-a', '-G', 'dialout', username],
                                   check=True)
                    print_status("Please log out and back in for changes to take effect")
                else:
                    print_status("User already in dialout group")
        except Exception as e:
            print(f"WARNING: Could not setup serial permissions: {e}")


def main():
    """Main entry point"""
    print("=" * 60)
    print("One-Way Clutch Tester - Installation Script")
    print("=" * 60)

    if post_clone_setup():
        print("\n" + "=" * 60)
        print("INSTALLATION SUCCESSFUL!")
        print("Next steps:")
        print("1. Look for the desktop shortcut 'One-Way Clutch Tester'")
        print("2. Double-click it to run the application")
        print("3. On Linux, you may need to log out/in for serial permissions")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("INSTALLATION FAILED!")
        print("Please check the error messages above and try again.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())