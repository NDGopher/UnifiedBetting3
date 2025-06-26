import os
import subprocess
import sys
import webbrowser
from pathlib import Path
import json
import shutil
import socket
import time
import logging
import threading
import platform
import signal
import psutil
import atexit
import ctypes
import msvcrt
import win32gui
import win32con
import win32api

# Configure Windows console for colors
if platform.system() == "Windows":
    try:
        # Enable ANSI color support
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass

# Color codes for Windows PowerShell
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

def print_banner():
    """Print a beautiful banner"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                    UNIFIED BETTING APP                       ║
║                        LAUNCHER                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)

def print_status(message, status="INFO", color=Colors.WHITE):
    """Print a formatted status message"""
    timestamp = time.strftime("%H:%M:%S")
    status_colors = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "PROGRESS": Colors.CYAN
    }
    status_color = status_colors.get(status, Colors.WHITE)
    print(f"{Colors.GRAY}[{timestamp}]{Colors.RESET} {status_color}[{status}]{Colors.RESET} {color}{message}{Colors.RESET}")

def print_progress(current, total, description=""):
    """Print a progress bar"""
    bar_length = 40
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    percentage = current * 100 // total
    print(f"\r{Colors.CYAN}[PROGRESS]{Colors.RESET} {description} |{bar}| {percentage}%", end='', flush=True)
    if current == total:
        print()  # New line when complete

# Configure logging with custom formatter
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        # Add colors to log levels
        if record.levelno >= logging.ERROR:
            color = Colors.RED
        elif record.levelno >= logging.WARNING:
            color = Colors.YELLOW
        elif record.levelno >= logging.INFO:
            color = Colors.BLUE
        else:
            color = Colors.GRAY
        
        # Format the message
        formatted = super().format(record)
        return f"{color}{formatted}{Colors.RESET}"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apply colored formatter
for handler in logger.handlers:
    handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Global variables to track processes
backend_process = None
frontend_process = None
chrome_processes = []
all_child_processes = []
cleanup_done = False

def handle_chrome_restore_dialog():
    """Automatically handle Chrome restore dialog if it appears"""
    try:
        import win32gui
        import win32con
        import win32api
        import time
        
        # Wait a moment for the dialog to appear
        time.sleep(2)
        
        # Look for Chrome restore dialog window with multiple approaches
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                # Look for various restore dialog variations
                if any(keyword in window_text.lower() for keyword in [
                    'restore', 'chrome', 'session', 'reopen', 'recovery'
                ]):
                    windows.append((hwnd, window_text))
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        for hwnd, window_text in windows:
            try:
                print_status(f"Found Chrome dialog: {window_text}", "INFO", Colors.YELLOW)
                
                # Try multiple approaches to close the dialog
                # Method 1: Send Alt+N (Don't restore)
                win32api.SendMessage(hwnd, win32con.WM_SYSKEYDOWN, ord('N'), 0x001C0001)
                win32api.SendMessage(hwnd, win32con.WM_SYSKEYUP, ord('N'), 0xC01C0001)
                time.sleep(0.5)
                
                # Method 2: Send Escape key
                win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_ESCAPE, 0)
                win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_ESCAPE, 0)
                time.sleep(0.5)
                
                # Method 3: Send Enter key
                win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                
                print_status("✅ Automatically handled Chrome restore dialog", "SUCCESS", Colors.GREEN)
                return True
            except Exception as e:
                print_status(f"Failed to handle dialog: {e}", "WARNING", Colors.YELLOW)
                continue
    except Exception as e:
        print_status(f"Chrome restore dialog handling failed: {e}", "WARNING", Colors.YELLOW)
    return False

def cleanup_on_exit():
    """Cleanup function to be called when the script exits"""
    global cleanup_done
    if cleanup_done:
        return
    cleanup_done = True
    
    print_status("🔄 Force cleaning up ALL processes and windows...", "PROGRESS", Colors.YELLOW)
    print_status("💡 If Chrome shows a 'restore pages' dialog, click 'Don't restore'", "INFO", Colors.YELLOW)
    
    # Kill backend and frontend processes
    if backend_process and backend_process.poll() is None:
        print_status("Force killing backend process...", "INFO", Colors.BLUE)
        try:
            backend_process.kill()
        except:
            pass
    
    if frontend_process and frontend_process.poll() is None:
        print_status("Force killing frontend process...", "INFO", Colors.BLUE)
        try:
            frontend_process.kill()
        except:
            pass
    
    # Kill all child processes aggressively
    for proc in all_child_processes:
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except:
                pass
    
    # Force kill ALL Chrome processes (this is the main issue)
    print_status("Force killing ALL Chrome processes...", "INFO", Colors.RED)
    try:
        subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
        subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
        
        # Wait a moment for Chrome to potentially show restore dialog
        time.sleep(1)
        
        # Automatically handle Chrome restore dialog if it appears
        handle_chrome_restore_dialog()
        
    except:
        pass
    
    # Close Chrome windows related to the app
    close_chrome_windows()
    
    # Kill processes on our ports aggressively
    for port in [5001, 3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009, 3010]:
        kill_process_on_port(port)
    
    # Force kill any remaining node and python processes related to our app
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name']:
                    name = proc.info['name'].lower()
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Kill ALL node processes (they might be running our frontend)
                    if name == 'node.exe':
                        print_status(f"Force killing Node process: {proc.info['pid']}", "INFO", Colors.YELLOW)
                        proc.kill()
                    
                    # Kill ALL python processes (they might be running our backend)
                    elif name == 'python.exe':
                        print_status(f"Force killing Python process: {proc.info['pid']}", "INFO", Colors.YELLOW)
                        proc.kill()
                    
                    # Kill ALL Chrome processes
                    elif name == 'chrome.exe' or name == 'chromedriver.exe':
                        print_status(f"Force killing Chrome process: {proc.info['pid']}", "INFO", Colors.YELLOW)
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except:
        pass
    
    print_status("✅ Force cleanup complete!", "SUCCESS", Colors.GREEN)

def close_chrome_windows():
    """Close Chrome windows related to the betting app"""
    try:
        import psutil
        
        print_status("🔍 Force closing ALL Chrome windows...", "INFO", Colors.CYAN)
        
        # Force kill ALL Chrome processes
        try:
            subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
            subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
            print_status("✅ All Chrome processes force killed", "SUCCESS", Colors.GREEN)
        except:
            pass
        
        # Also try to find and kill specific Chrome processes
        chrome_closed = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    print_status(f"Force killing Chrome process: {proc.info['pid']}", "INFO", Colors.YELLOW)
                    try:
                        proc.kill()
                        chrome_closed = True
                    except:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if not chrome_closed:
            print_status("No additional Chrome processes found", "INFO", Colors.GRAY)
                
    except Exception as e:
        print_status(f"Error closing Chrome windows: {e}", "ERROR", Colors.RED)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print_status(f"🛑 Received signal {signum}, shutting down...", "WARNING", Colors.YELLOW)
    cleanup_on_exit()
    sys.exit(0)

def windows_console_handler(event_type):
    """Handle Windows console events for better cleanup"""
    if event_type in [signal.CTRL_C_EVENT, signal.CTRL_BREAK_EVENT]:
        print_status("Received shutdown signal, cleaning up...", "INFO", Colors.YELLOW)
        cleanup_on_exit()
        sys.exit(0)
    elif event_type == signal.CTRL_CLOSE_EVENT:
        print_status("Console window closing, cleaning up...", "INFO", Colors.YELLOW)
        cleanup_on_exit()
        sys.exit(0)

# Set up signal handlers for Windows
if platform.system() == "Windows":
    try:
        # Register for console events
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCtrlHandler(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)(windows_console_handler), True)
        
        # Also set up Python signal handlers as backup
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register cleanup function to run on exit
        atexit.register(cleanup_on_exit)
        
    except Exception as e:
        print_status(f"Warning: Could not set up Windows signal handlers: {e}", "WARNING", Colors.YELLOW)
        # Fallback to Python signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        atexit.register(cleanup_on_exit)
else:
    # Unix-like systems
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_on_exit)

def find_free_port(start_port=3000, max_port=3010):
    """Find a free port in the given range"""
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return None

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    try:
        import psutil
    except ImportError:
        print_status("psutil not found, attempting to install...", "WARNING", Colors.YELLOW)
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import psutil
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections():
                if conn.laddr.port == port:
                    print_status(f"Killing process on port {port}", "INFO", Colors.YELLOW)
                    proc.kill()
                    time.sleep(0.5)  # Reduced wait time
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def run_command(command, cwd=None, silent=False):
    """Run a command and print its output in real-time"""
    if not silent:
        print_status(f"Running command: {command}", "INFO", Colors.GRAY)
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE if silent else None,
        stderr=subprocess.STDOUT if silent else None,
        text=True,
        shell=True,
        cwd=cwd
    )
    
    # Track the process for cleanup
    all_child_processes.append(process)
    
    if silent:
        # For silent commands, just wait and return the result
        process.wait()
        if process.returncode != 0:
            print_status(f"Silent command failed with return code {process.returncode}", "ERROR", Colors.RED)
    else:
        process.wait()
        if process.returncode != 0:
            print_status(f"Command failed with return code {process.returncode}", "ERROR", Colors.RED)
    
    return process

def check_dependencies_installed(backend_dir, frontend_dir):
    """Check if dependencies are already installed"""
    backend_venv = backend_dir / "venv"
    frontend_node_modules = frontend_dir / "node_modules"
    
    # Check if uvicorn is installed in the virtual environment
    if sys.platform == "win32":
        pip_cmd = str(backend_dir / "venv" / "Scripts" / "pip")
    else:
        pip_cmd = str(backend_dir / "venv" / "bin" / "pip")
    
    try:
        result = subprocess.run(
            f'"{pip_cmd}" show uvicorn',
            shell=True,
            capture_output=True,
            text=True
        )
        uvicorn_installed = result.returncode == 0
    except:
        uvicorn_installed = False
    
    return backend_venv.exists() and frontend_node_modules.exists() and uvicorn_installed

def check_for_problematic_files(directory):
    """Check for problematic files like '-' and remove them"""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file == '-':
                file_path = os.path.join(root, file)
                print_status(f"Removing problematic file: {file_path}", "WARNING", Colors.YELLOW)
                try:
                    os.remove(file_path)
                except Exception as e:
                    print_status(f"Error removing file {file_path}: {e}", "ERROR", Colors.RED)

def setup_pto_profile(backend_dir, python_cmd):
    """Setup PTO Chrome profile if needed"""
    print_status("=== Checking PTO Chrome Profile ===", "INFO", Colors.BLUE)
    
    config_path = backend_dir / "config.json"
    if not config_path.exists():
        print_status("config.json not found, PTO setup will be needed", "WARNING", Colors.YELLOW)
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        pto_config = config.get("pto", {})
        profile_dir = pto_config.get("chrome_user_data_dir")
        
        # Check if profile already exists and is working
        if profile_dir and os.path.exists(profile_dir):
            print_status("PTO profile directory exists, testing...", "INFO", Colors.BLUE)
            
            # More robust test that handles Chrome restore dialogs
            test_cmd = f'{python_cmd} -c "from pto_scraper import PTOScraper; import json; config=json.load(open(\'config.json\')); scraper=PTOScraper(config[\'pto\']); result=scraper.test_profile(); print(\'Profile test result:\', result)"'
            result = subprocess.run(test_cmd, shell=True, cwd=backend_dir, capture_output=True, text=True, timeout=30)
            
            # Handle Chrome restore dialog if it appears during testing
            time.sleep(2)  # Wait for Chrome to potentially show dialog
            handle_chrome_restore_dialog()
            
            if "Profile test result: True" in result.stdout:
                print_status("✅ PTO profile is working correctly", "SUCCESS", Colors.GREEN)
            elif "Profile test result: False" in result.stdout:
                print_status("⚠️ PTO profile test failed - may need setup", "WARNING", Colors.YELLOW)
                print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to fix this", "INFO", Colors.GRAY)
            else:
                # Check if it's a Chrome restore dialog issue
                if "restore" in result.stderr.lower() or "restore" in result.stdout.lower():
                    print_status("⚠️ Chrome restore dialog detected - profile may need attention", "WARNING", Colors.YELLOW)
                    print_status("💡 Please close any Chrome restore dialogs and try again", "INFO", Colors.GRAY)
                else:
                    print_status("⚠️ PTO profile test failed - will need setup", "WARNING", Colors.YELLOW)
                    print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to fix this", "INFO", Colors.GRAY)
        else:
            print_status("ℹ️ PTO profile not found - will need setup", "INFO", Colors.YELLOW)
            print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up", "INFO", Colors.GRAY)
            
    except Exception as e:
        print_status(f"Error checking PTO profile: {e}", "ERROR", Colors.RED)
        print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up", "INFO", Colors.GRAY)
        return False

def open_pinnacle_odds_dropper():
    """Open pinnacleoddsdropper.com in default browser"""
    print_status("=== Opening Pinnacle Odds Dropper ===", "INFO", Colors.BLUE)
    try:
        url = "https://pinnacleoddsdropper.com"
        print_status(f"Opening {url} in default browser...", "INFO", Colors.BLUE)
        webbrowser.open(url)
        print_status("✅ Pinnacle Odds Dropper opened successfully", "SUCCESS", Colors.GREEN)
        return True
    except Exception as e:
        print_status(f"Failed to open Pinnacle Odds Dropper: {e}", "ERROR", Colors.RED)
        return False

def refresh_pinnacle_odds_dropper():
    """Refresh the Pinnacle Odds Dropper tab to ensure Chrome extension is working"""
    print_status("=== Refreshing Pinnacle Odds Dropper ===", "INFO", Colors.BLUE)
    try:
        url = "https://pinnacleoddsdropper.com"
        print_status(f"Refreshing {url} in existing browser window...", "INFO", Colors.BLUE)
        webbrowser.open(url, new=1)  # new=1 refreshes existing window
        print_status("✅ Pinnacle Odds Dropper refreshed successfully", "SUCCESS", Colors.GREEN)
        return True
    except Exception as e:
        print_status(f"Failed to refresh Pinnacle Odds Dropper: {e}", "ERROR", Colors.RED)
        return False

def setup_backend():
    """Set up the backend environment and install dependencies"""
    print_status("=== Setting up Backend ===", "INFO", Colors.BLUE)
    backend_dir = Path("backend")
    
    # Create virtual environment if it doesn't exist
    if not (backend_dir / "venv").exists():
        print_status("Creating virtual environment...", "INFO", Colors.BLUE)
        if run_command("python -m venv venv", cwd=backend_dir).wait() != 0:
            raise Exception("Failed to create virtual environment")
    
    # Activate virtual environment and install dependencies
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate.bat"
        python_cmd = "venv\\Scripts\\python"
    else:
        activate_cmd = "venv/bin/activate"
        python_cmd = "venv/bin/python"
    
    # Check if dependencies are already installed
    if (backend_dir / "requirements.txt").exists():
        # Check if uvicorn is already installed (indicator that dependencies are installed)
        try:
            result = subprocess.run(
                f'"{python_cmd}" -c "import uvicorn; print(\'deps_installed\')"',
                shell=True,
                cwd=backend_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            deps_installed = "deps_installed" in result.stdout
        except:
            deps_installed = False
        
        if not deps_installed:
            print_status("Installing backend dependencies...", "INFO", Colors.BLUE)
            # First upgrade pip to avoid warnings (silent)
            if run_command(f"{python_cmd} -m pip install --upgrade pip", cwd=backend_dir, silent=True).wait() != 0:
                raise Exception("Failed to upgrade pip")
            
            # Then install requirements (silent)
            if run_command(f"{python_cmd} -m pip install -r requirements.txt", cwd=backend_dir, silent=True).wait() != 0:
                raise Exception("Failed to install backend requirements")
            
            print_status("✅ Backend dependencies installed successfully", "SUCCESS", Colors.GREEN)
        else:
            print_status("✅ Backend dependencies already installed", "SUCCESS", Colors.GREEN)
    else:
        print_status("requirements.txt not found in backend directory", "WARNING", Colors.YELLOW)
    
    return python_cmd

def setup_frontend():
    """Set up the frontend environment and install dependencies"""
    print_status("=== Setting up Frontend ===", "INFO", Colors.BLUE)
    frontend_dir = Path("frontend")
    
    # Check if node_modules already exists
    if (frontend_dir / "node_modules").exists():
        print_status("✅ Frontend dependencies already installed", "SUCCESS", Colors.GREEN)
    else:
        print_status("Installing frontend dependencies...", "INFO", Colors.BLUE)
        if run_command("npm install", cwd=frontend_dir, silent=True).wait() != 0:
            raise Exception("Failed to install frontend dependencies")
        
        print_status("✅ Frontend dependencies installed successfully", "SUCCESS", Colors.GREEN)

def wait_for_backend(port=5001, timeout=30):
    """Wait for backend to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', port))
                return True
        except:
            time.sleep(0.5)
    return False

def launch_application():
    """Launch both backend and frontend servers with PTO integration"""
    global backend_process, frontend_process
    
    try:
        # Print beautiful banner
        print_banner()
        print_status("🚀 Launching Unified Betting Application...", "INFO", Colors.CYAN)
        
        # Get the absolute path to the project directory
        project_dir = Path(__file__).parent.absolute()
        os.chdir(project_dir)
        print_status(f"Project directory: {project_dir}", "INFO", Colors.GRAY)
        
        # Check for problematic files
        check_for_problematic_files(project_dir)
        
        # Check PTO profile automatically without prompting
        backend_dir = project_dir / "backend"
        python_cmd = sys.executable
        
        print_status("🔍 Checking PTO profile configuration...", "INFO", Colors.BLUE)
        
        # Check if PTO profile exists and is working
        config_path = backend_dir / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                pto_config = config.get("pto", {})
                profile_dir = pto_config.get("chrome_user_data_dir")
                
                if profile_dir and os.path.exists(profile_dir):
                    print_status("PTO profile directory exists, testing...", "INFO", Colors.BLUE)
                    
                    # More robust test that handles Chrome restore dialogs
                    test_cmd = f'{python_cmd} -c "from pto_scraper import PTOScraper; import json; config=json.load(open(\'config.json\')); scraper=PTOScraper(config[\'pto\']); result=scraper.test_profile(); print(\'Profile test result:\', result)"'
                    result = subprocess.run(test_cmd, shell=True, cwd=backend_dir, capture_output=True, text=True, timeout=30)
                    
                    # Handle Chrome restore dialog if it appears during testing
                    time.sleep(2)  # Wait for Chrome to potentially show dialog
                    handle_chrome_restore_dialog()
                    
                    if "Profile test result: True" in result.stdout:
                        print_status("✅ PTO profile is working correctly", "SUCCESS", Colors.GREEN)
                    elif "Profile test result: False" in result.stdout:
                        print_status("⚠️ PTO profile test failed - may need setup", "WARNING", Colors.YELLOW)
                        print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to fix this", "INFO", Colors.GRAY)
                    else:
                        # Check if it's a Chrome restore dialog issue
                        if "restore" in result.stderr.lower() or "restore" in result.stdout.lower():
                            print_status("⚠️ Chrome restore dialog detected - profile may need attention", "WARNING", Colors.YELLOW)
                            print_status("💡 Please close any Chrome restore dialogs and try again", "INFO", Colors.GRAY)
                        else:
                            print_status("⚠️ PTO profile test failed - will need setup", "WARNING", Colors.YELLOW)
                            print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to fix this", "INFO", Colors.GRAY)
                else:
                    print_status("ℹ️ PTO profile not found - will need setup", "INFO", Colors.YELLOW)
                    print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up", "INFO", Colors.GRAY)
            except Exception as e:
                print_status(f"Error checking PTO profile: {e}", "ERROR", Colors.RED)
                print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up", "INFO", Colors.GRAY)
        else:
            print_status("config.json not found, PTO setup will be needed", "WARNING", Colors.YELLOW)
            print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up", "INFO", Colors.GRAY)
        
        # Continue with the rest of the launch sequence
        print_status("🔍 Checking for existing processes...", "INFO", Colors.BLUE)
        
        # Kill any existing processes on ports 3000-3010 and 5001
        for port in range(3000, 3011):
            kill_process_on_port(port)
        kill_process_on_port(5001)
        
        # Find free ports
        frontend_port = find_free_port(3000, 3010)
        if not frontend_port:
            raise Exception("Could not find a free port for the frontend")
        print_status(f"Using frontend port: {frontend_port}", "INFO", Colors.GREEN)
        
        # Always set up environments to ensure dependencies are installed
        print_status("📦 Setting up backend environment...", "INFO", Colors.BLUE)
        python_cmd = setup_backend()
        
        print_status("📦 Setting up frontend environment...", "INFO", Colors.BLUE)
        setup_frontend()
        
        # Open Pinnacle Odds Dropper
        print_status("🌐 Opening Pinnacle Odds Dropper...", "INFO", Colors.BLUE)
        open_pinnacle_odds_dropper()
        
        # Launch backend server
        print_status("🚀 Starting Backend (FastAPI/Uvicorn) on port 5001...", "INFO", Colors.CYAN)
        
        # Use relative paths for better portability
        if sys.platform == "win32":
            activate_cmd = f'cd {backend_dir} && call venv\\Scripts\\activate.bat && set PYTHONPATH={project_dir} && {backend_dir}\\venv\\Scripts\\python.exe -m uvicorn main:app --host 0.0.0.0 --port 5001 --no-access-log'
        else:
            activate_cmd = f'cd {backend_dir} && source venv/bin/activate && PYTHONPATH={project_dir} {backend_dir}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 5001 --no-access-log'
        
        backend_process = subprocess.Popen(
            activate_cmd,
            cwd=backend_dir,  # Set working directory to backend directory
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        # Track backend process for cleanup
        all_child_processes.append(backend_process)
        
        # Log backend output in a separate thread
        pto_monitoring_ready = threading.Event()
        
        def log_backend_output():
            while backend_process.poll() is None:
                output = backend_process.stdout.readline()
                if output:
                    output = output.strip()
                    
                    # Skip all the verbose Chrome/DevTools/USB/TensorFlow noise
                    skip_patterns = [
                        'DevTools listening on ws://',
                        'WARNING: All log messages',
                        'Created TensorFlow Lite XNNPACK delegate',
                        'Attempting to use a delegate',
                        'USB: usb_service_win.cc',
                        'voice_transcription',
                        'DEP_WEBPACK_DEV_SERVER',
                        'Requirement already satisfied',
                        'INFO:     Uvicorn running',
                        'INFO:     Started reloader process',
                        'INFO:     Will watch for changes',
                        'Opening in existing browser session',
                        'Page loaded into a non-browser-tab context',
                        'Use `node --trace-deprecation`',
                        'components\\device_event_log\\device_event_log_impl.cc',
                        'SetupDiGetDeviceProperty',
                        'Registering VoiceTranscriptionCapability',
                        'TensorFlow Lite XNNPACK delegate',
                        'static-sized tensors',
                        'dynamic-sized tensors',
                        'content\\browser\\network_service_instance_impl.cc',
                        'content\\browser\\gpu\\gpu_process_host.cc',
                        'GPU process exited unexpectedly',
                        'Network service crashed',
                        'ERROR:components\\device_event_log',
                        'USB: usb_service_win.cc:105',
                        'WARNING: All log messages before absl::InitializeLog()',
                        'voice_transcription.cc:58',
                        'Created TensorFlow Lite XNNPACK delegate for CPU',
                        'Attempting to use a delegate that only supports static-sized tensors',
                        'dynamic-sized tensors (tensor#-1 is a dynamic-sized tensor)',
                        'DevTools listening on ws://127.0.0.1:',
                        'components\\device_event_log\\device_event_log_impl.cc:202',
                        'ERROR:content\\browser\\network_service_instance_impl.cc',
                        'Network service crashed, restarting service',
                        'USB: usb_service_win.cc:105 SetupDiGetDeviceProperty',
                        'Element not found. (0x490)',
                        'I0000 00:00:',
                        'voice_transcription.cc:58] Registering VoiceTranscriptionCapability',
                        'Created TensorFlow Lite XNNPACK delegate for CPU.',
                        'Attempting to use a delegate that only supports static-sized tensors with a graph that has dynamic-sized tensors'
                    ]
                    
                    if any(pattern in output for pattern in skip_patterns):
                        continue
                    
                    # Clean up and format important messages
                    if 'telegram_alerts' in output and 'configured' in output:
                        print(f"{Colors.YELLOW}📱 Telegram Alerts configured!{Colors.RESET}")
                    elif 'pto_scraper' in output and 'started' in output:
                        print(f"{Colors.CYAN}🤖 PTO Scraper started{Colors.RESET}")
                    elif 'Server ready to receive alerts' in output:
                        print(f"{Colors.GREEN}✅ Server ready to receive alerts{Colors.RESET}")
                    elif 'Chrome driver created successfully' in output:
                        print(f"{Colors.GREEN}✅ Chrome driver created successfully{Colors.RESET}")
                    elif 'Successfully passed Cloudflare challenge' in output:
                        print(f"{Colors.GREEN}✅ Successfully passed Cloudflare challenge{Colors.RESET}")
                    elif 'PTO setup complete' in output and 'prop monitoring' in output:
                        print(f"{Colors.GREEN}✅ PTO successfully monitoring props{Colors.RESET}")
                        # Set flag when PTO is actually monitoring
                        pto_monitoring_ready.set()
                    elif 'Could not switch to Prop Builder tab' in output:
                        # This is often a false positive - PTO usually works anyway
                        print(f"{Colors.YELLOW}⚠️ Prop Builder tab warning (usually works anyway){Colors.RESET}")
                    elif 'Still on Cloudflare page, waiting longer' in output:
                        # Skip this warning - only show if it actually fails
                        continue
                    elif 'error' in output.lower() or 'exception' in output.lower():
                        print(f"{Colors.RED}❌ {output}{Colors.RESET}")
                    elif 'warning' in output.lower():
                        print(f"{Colors.YELLOW}⚠️ {output}{Colors.RESET}")
        
        backend_log_thread = threading.Thread(target=log_backend_output, daemon=True)
        backend_log_thread.start()
        
        # Wait for backend to be ready
        print_status("⏳ Waiting for backend to start...", "INFO", Colors.YELLOW)
        
        # Show progress while waiting
        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', 5001))
                    print_status("✅ Backend is ready!", "SUCCESS", Colors.GREEN)
                    break
            except:
                elapsed = int(time.time() - start_time)
                print(f"\r{Colors.YELLOW}[PROGRESS]{Colors.RESET} Waiting for backend... {elapsed}s", end='', flush=True)
                time.sleep(0.5)
        else:
            print()  # New line after progress
            print_status("Backend failed to start within 30 seconds", "ERROR", Colors.RED)
            backend_process.terminate()
            raise Exception("Backend startup timeout")
        
        # Launch frontend server
        frontend_dir = project_dir / "frontend"
        print_status(f"🚀 Starting Frontend (React) on port {frontend_port}...", "INFO", Colors.CYAN)
        
        # Set the port for React
        env = os.environ.copy()
        env['PORT'] = str(frontend_port)
        frontend_process = subprocess.Popen(
            "npm start",
            cwd=frontend_dir,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        # Track frontend process for cleanup
        all_child_processes.append(frontend_process)
        
        # Log frontend output in a separate thread
        frontend_ready_flag = threading.Event()
        
        def log_frontend_output():
            while frontend_process.poll() is None:
                output = frontend_process.stdout.readline()
                if output:
                    output = output.strip()
                    
                    # Skip all the verbose noise
                    skip_patterns = [
                        'DevTools listening on ws://',
                        'WARNING: All log messages',
                        'Created TensorFlow Lite XNNPACK delegate',
                        'Attempting to use a delegate',
                        'USB: usb_service_win.cc',
                        'voice_transcription',
                        'DEP_WEBPACK_DEV_SERVER',
                        'node:',
                        'Opening in existing browser session'
                    ]
                    
                    if any(pattern in output for pattern in skip_patterns):
                        continue
                    
                    # Clean up and format important messages
                    if 'Starting the development server' in output:
                        print(f"{Colors.MAGENTA}🚀 Starting React development server...{Colors.RESET}")
                    elif 'Compiled successfully' in output:
                        print(f"{Colors.GREEN}✅ Frontend compiled successfully{Colors.RESET}")
                        # Set flag when frontend is actually ready
                        frontend_ready_flag.set()
                    elif 'Local:' in output and 'localhost:' in output:
                        print(f"{Colors.GREEN}🌐 {output}{Colors.RESET}")
                    elif 'error' in output.lower() or 'failed' in output.lower():
                        print(f"{Colors.RED}❌ {output}{Colors.RESET}")
                    elif 'warning' in output.lower():
                        print(f"{Colors.YELLOW}⚠️ {output}{Colors.RESET}")
        
        frontend_log_thread = threading.Thread(target=log_frontend_output, daemon=True)
        frontend_log_thread.start()
        
        # Wait a bit for frontend to start
        print_status("⏳ Waiting for frontend to start...", "INFO", Colors.YELLOW)
        time.sleep(3)
        
        # Wait for frontend to be actually ready
        frontend_ready = False
        start_time = time.time()
        while time.time() - start_time < 30 and not frontend_ready:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', frontend_port))
                    frontend_ready = True
                    break
            except:
                time.sleep(1)
        
        if not frontend_ready:
            print_status("Frontend failed to start within 30 seconds", "ERROR", Colors.RED)
            frontend_process.terminate()
            raise Exception("Frontend startup timeout")
        
        # Wait for frontend to actually compile successfully
        print_status("⏳ Waiting for frontend to compile...", "INFO", Colors.YELLOW)
        if not frontend_ready_flag.wait(timeout=60):  # Wait up to 60 seconds for compilation
            print_status("Frontend compilation timeout", "WARNING", Colors.YELLOW)
        
        # Wait for PTO to actually be monitoring props
        print_status("⏳ Waiting for PTO to start monitoring...", "INFO", Colors.YELLOW)
        if not pto_monitoring_ready.wait(timeout=120):  # Wait up to 2 minutes for PTO monitoring
            print_status("PTO monitoring timeout", "WARNING", Colors.YELLOW)
        
        # Print success banner with next steps (only after everything is truly ready)
        success_banner = f"""
{Colors.GREEN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                🎉 LAUNCH SUCCESSFUL! 🎉                      ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
{Colors.CYAN}📊 Frontend:{Colors.RESET} http://localhost:{frontend_port}
{Colors.CYAN}🔧 Backend API:{Colors.RESET} http://localhost:5001
{Colors.CYAN}📈 Pinnacle Odds Dropper:{Colors.RESET} https://pinnacleoddsdropper.com
{Colors.CYAN}✅ PTO Scraper:{Colors.RESET} Active and monitoring

{Colors.YELLOW}{Colors.BOLD}📋 NEXT STEPS:{Colors.RESET}
{Colors.WHITE}1. Log in to betbck.com{Colors.RESET}
{Colors.WHITE}2. Refresh pinnacleoddsdropper.com{Colors.RESET}
{Colors.WHITE}3. Confirm PickTheOdds is showing Prop Builder{Colors.RESET}
{Colors.WHITE}4. Open http://localhost:{frontend_port} in your browser{Colors.RESET}

{Colors.YELLOW}💡 Press Ctrl+C to stop all services{Colors.RESET}
{Colors.YELLOW}💡 Close this window to automatically clean up all processes and windows{Colors.RESET}
{Colors.GREEN}══════════════════════════════════════════════════════════════════{Colors.RESET}
"""
        print(success_banner)
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
                if backend_process.poll() is not None:
                    print_status("Backend process died unexpectedly", "ERROR", Colors.RED)
                    break
                if frontend_process.poll() is not None:
                    print_status("Frontend process died unexpectedly", "ERROR", Colors.RED)
                    break
        except KeyboardInterrupt:
            print_status("Shutting down services...", "WARNING", Colors.YELLOW)
            cleanup_on_exit()
    except Exception as e:
        print_status(f"Failed to launch application: {e}", "ERROR", Colors.RED)
        cleanup_on_exit()
        raise

if __name__ == "__main__":
    launch_application() 