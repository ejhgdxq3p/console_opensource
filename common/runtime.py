import os
import sys
import __main__ as main


def _get_paths():
    """Determine paths based on whether running as PyInstaller bundle or normal Python."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle (single exe or folder)
        # sys._MEIPASS is the temp folder where files are extracted
        bundle_dir = sys._MEIPASS
        # For exe, use the directory where the exe is located for data storage
        exe_dir = os.path.dirname(sys.executable)
        return bundle_dir, exe_dir
    else:
        # Running in normal Python environment
        console_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        base_path = os.path.dirname(console_path)
        return console_path, base_path


# Get paths
_console_path, base_path = _get_paths()

service_name = "unknown"
current_task_id = ""
config = None
# Debugging function can be enabled by setting the environment variable MRI4ALL_DEBUG to "true"
debugging_enabled = os.getenv("MRI4ALL_DEBUG", "").lower() == "true"


def set_service_name(name):
    """Set the service name. This is used across the framework to identify the current service."""
    global service_name
    service_name = name


def get_service_name():
    """Get the service name."""
    return service_name


def get_base_path():
    """Get the base path of the MRI4ALL installation."""
    return base_path


def get_console_path():
    """Get the console path of the MRI4ALL installation."""
    return _console_path


def set_current_task_id(task_id: str):
    """Set the currently processed task ID."""
    global current_task_id
    current_task_id = task_id


def get_current_task_id() -> str:
    """Get the currently processed task ID. If no task is currently processed, an empty string is returned."""
    global current_task_id
    return current_task_id


def clear_current_task_id():
    """Clear the currently processed task ID."""
    global current_task_id
    current_task_id = ""


def is_debugging_enabled():
    """Returns True if debugging is enabled."""
    return debugging_enabled


def set_debug(new_state):
    global debugging_enabled
    debugging_enabled = new_state
