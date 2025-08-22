````markdown
# One Way Clutch Controller

## 📌 Overview
This project provides a GUI-based application for controlling and monitoring a motor controller.  
It is built using **Python**, **Tkinter**, and **Serial Communication**.  
All key configurations (like COM port) can be modified in `constants.py`.

---

## 🛠️ Prerequisites
Before running the project, ensure you have:
- **Python 3.12+** installed  
- **Git** installed  
- A working COM port connection to your hardware

---

## 📥 Installation

### 1️⃣ Clone the Repository
```bash
git clone <your-repo-url>
cd One_way_Clutch
````

### 2️⃣ Create and Activate Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3️⃣ Install Required Libraries

Install all dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### 1. Set the Correct COM Port

Edit:

```
src/constants/constants.py
```

Locate:

```python
COM_PORT = "COM3"  # Example value
```

Replace `"COM3"` with your system’s correct COM port:

* On **Windows**: `"COM4"`, `"COM5"`, etc.
* On **Linux/Mac**: `/dev/ttyUSB0`, `/dev/ttyS1`, etc.

---

## ▶️ Running the Application

From the **project root folder**, run:

```bash
python -m src.gui.gui
```

This will:

* Launch the GUI
* Initialize the motor controller connection
* Start updating live parameters

---

## 📂 Project Structure

```
Project_Name/
│
├── src/
│   ├── gui/
│   │   └── gui.py                # Main GUI application
│   ├── core/
│   │   └── motor_controller.py   # Motor control logic
│   ├── constants/
│   │   └── constants.py          # Configurable constants (COM port, etc.)
│   └── api/
│       └── start_OWC.bat  
        └── start_gui_api.bat     # Batch file to run the project (Windows)
│
├── venv/                         # Virtual environment (not in GitHub)
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

---

## 🐞 Troubleshooting

### `ModuleNotFoundError: No module named 'src'`

Make sure you are running the script from the **project root**:

```bash
python -m src.gui.gui
```

### Missing Library Error

Install it manually:

```bash
pip install <library-name>
```

Then update your `requirements.txt`:

```bash
pip freeze > requirements.txt
```

