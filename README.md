# MRI4ALL Console

This repository contains the console software for the Zeugmatron Z1 MRI scanner that was developed during the MRI4ALL Hackathon 2023. The software has been built solely using open-source components. It runs under the Ubuntu 22.04 operating system and has been written in Python 3 using PyQt5 for the graphical user interface. A development environment with  automatic installation is provided. Installation instructions are provided in the [Wiki](https://github.com/mri4all/console/wiki).

![Screenshot from 2024-02-22 21-09-10](https://github.com/mri4all/console/assets/35747793/2da37f29-bd7a-491e-81ea-2f57ce5ae4b2)


## Software Overview and Platform Architecture

The <a href="https://www.youtube.com/embed/8GNmocJP-14" target="_blank">video below</a> provides an overview & demo of the MRI4ALL Console Software. It also gives a brief introduction to the underlying software architecture and explains how custom sequences and reconstruction techniques can be integrated.

[![Overview of the MRI4ALL Console Software](https://img.youtube.com/vi/8GNmocJP-14/0.jpg)](https://www.youtube.com/watch?v=8GNmocJP-14)

---

## Windows Development Environment Setup

The software can also run on Windows for development and testing purposes (without MRI hardware connection).

### Prerequisites

- Python 3.10+ installed with pip
- Ensure "Add Python to PATH" is checked during installation

### Step 1: Create Virtual Environment

```powershell
cd C:\path\to\console_opensource

# Create virtual environment
python -m venv venv

# If pip is missing, install it manually
Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py
.\venv\Scripts\python.exe get-pip.py
```

### Step 2: Install Dependencies

```powershell
.\venv\Scripts\python.exe -m pip install PyQt5 pyqtdarktheme pyqtgraph qtawesome matplotlib numpy scipy pydantic PyYAML pydicom nibabel h5py Pillow plotly tqdm numba msgpack
```

### Step 3: Create Data Directories

The application requires the following directory structure. Run this PowerShell command to create them:

```powershell
$basePath = Split-Path -Parent (Get-Location)
$dataPath = Join-Path $basePath "data"
$folders = @("acq_queue", "acq", "recon_queue", "recon", "complete", "failure", "archive", "state")
foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path (Join-Path $dataPath $folder)
}
```

**Directory Structure:**
```
parent_folder/
├── console_opensource/     ← Project code
│   ├── common/
│   ├── services/
│   ├── run_ui.py          ← Entry point
│   └── ...
└── data/                   ← Data directory (created above)
    ├── acq_queue/
    ├── acq/
    ├── recon_queue/
    ├── recon/
    ├── complete/
    ├── failure/
    ├── archive/
    └── state/
```

### Step 4: Run the Application

```powershell
.\venv\Scripts\python.exe run_ui.py
```

---

## Building Windows Executable (EXE)

You can package the application as a **single standalone Windows executable** using PyInstaller. Users can double-click the exe to run it directly.

### Step 1: Install PyInstaller

```powershell
.\venv\Scripts\python.exe -m pip install pyinstaller
```

### Step 2: Build the Executable

```powershell
.\venv\Scripts\pyinstaller.exe mri4all.spec --noconfirm
```

**Note:** The build process takes approximately 5-15 minutes. Wait until you see `Building EXE ... completed successfully`.

### Step 3: Distribute the Executable

After building, the **single exe file** will be located at:

```
dist\MRI4ALL.exe
```

This is a standalone file that can be:
- Copied to any location
- Shared with others
- Run by double-clicking (no Python installation required)

### Build Output Structure

```
console_opensource/
├── build/              ← Build temporary files (can be deleted)
├── dist/
│   └── MRI4ALL.exe     ← Single standalone executable (share this!)
└── mri4all.spec        ← PyInstaller configuration
```

### First Run Notes

When users run the exe for the first time:
1. Windows may show a security warning - click "More info" → "Run anyway"
2. The app will automatically create required `data` and `logs` folders next to the exe
3. First startup may take a few seconds as files are extracted

---

## Windows-Specific Notes

- **IPC Communication:** Inter-process communication (IPC) is disabled on Windows as it uses Unix-specific named pipes (mkfifo).
- **Service Control:** The acquisition and reconstruction services (systemctl) are skipped on Windows.
- **Hardware Connection:** MRI hardware connection is not available on Windows. Use Windows for UI development and testing only.

---

## Troubleshooting

### Common Issues on Windows

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Install missing package: `pip install <package_name>` |
| `mkfifo` error | This is automatically handled; IPC is disabled on Windows |
| VERSION file not found (in exe) | Ensure `VERSION` file is included in `mri4all.spec` datas |
| Virtual environment incomplete | Delete `venv` folder and recreate with `python -m venv venv` |

### Logs Location

Logs are stored in:
- Development: `<parent_folder>/logs/ui.log`
- Executable: Same location relative to the exe