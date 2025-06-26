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

def cleanup_on_exit():
    """Cleanup function to be called when the script exits"""
    print_status("🔄 Cleaning up processes and windows...", "PROGRESS", Colors.YELLOW)
    
    # Kill backend and frontend processes
    if backend_process and backend_process.poll() is None:
        print_status("Stopping backend process...", "INFO", Colors.BLUE)
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        except:
            backend_process.kill()
    
    if frontend_process and frontend_process.poll() is None:
        print_status("Stopping frontend process...", "INFO", Colors.BLUE)
        try:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
        except:
            frontend_process.kill()
    
    # Kill all child processes
    for proc in all_child_processes:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except:
                pass
    
    # Close Chrome windows related to the app
    close_chrome_windows()
    
    # Kill processes on our ports
    for port in [5001, 3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009, 3010]:
        kill_process_on_port(port)
    
    print_status("✅ Cleanup complete!", "SUCCESS", Colors.GREEN)

def close_chrome_windows():
    """Close Chrome windows related to the betting app"""
    try:
        import psutil
        
        # Keywords to identify our Chrome windows
        target_keywords = [
            'pinnacleoddsdropper.com',
            'betbck.com',
            'localhost:3000',
            'localhost:5001',
            'unified betting',
            'POD',
            'PTO'
        ]
        
        print_status("🔍 Looking for Chrome windows to close...", "INFO", Colors.CYAN)
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    # Check if this Chrome process has our target windows
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    for keyword in target_keywords:
                        if keyword.lower() in cmdline.lower():
                            print_status(f"Closing Chrome window with keyword: {keyword}", "INFO", Colors.YELLOW)
                            try:
                                proc.terminate()
                                time.sleep(0.5)
                            except:
                                pass
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
    except ImportError:
        print_status("psutil not available, skipping Chrome window cleanup", "WARNING", Colors.YELLOW)
    except Exception as e:
        print_status(f"Error closing Chrome windows: {e}", "ERROR", Colors.RED)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print_status(f"🛑 Received signal {signum}, shutting down...", "WARNING", Colors.YELLOW)
    cleanup_on_exit()
    sys.exit(0)

# Register cleanup function and signal handlers
atexit.register(cleanup_on_exit)
if hasattr(signal, 'SIGINT'):
    signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

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
    
    if not silent:
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
            test_cmd = f'{python_cmd} -c "from pto_scraper import PTOScraper; import json; config=json.load(open(\'config.json\')); scraper=PTOScraper(config[\'pto\']); print(\'Profile test:\', scraper.test_profile())"'
            result = subprocess.run(test_cmd, shell=True, cwd=backend_dir, capture_output=True, text=True)
            if "Profile test: True" in result.stdout:
                print_status("✅ PTO profile is working correctly", "SUCCESS", Colors.GREEN)
                return True
            else:
                print_status("⚠️ PTO profile exists but test failed", "WARNING", Colors.YELLOW)
                print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to fix this", "INFO", Colors.GRAY)
                return False
        else:
            print_status("ℹ️ PTO profile not found", "INFO", Colors.YELLOW)
            print_status("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up", "INFO", Colors.GRAY)
            return False
            
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
    
    # Always install requirements to ensure all dependencies are present
    if (backend_dir / "requirements.txt").exists():
        print_status("Installing backend dependencies...", "INFO", Colors.BLUE)
        # First upgrade pip to avoid warnings (silent)
        if run_command(f"{python_cmd} -m pip install --upgrade pip", cwd=backend_dir, silent=True).wait() != 0:
            raise Exception("Failed to upgrade pip")
        
        # Then install requirements (silent)
        if run_command(f"{python_cmd} -m pip install -r requirements.txt", cwd=backend_dir, silent=True).wait() != 0:
            raise Exception("Failed to install backend requirements")
        
        print_status("✅ Backend dependencies installed successfully", "SUCCESS", Colors.GREEN)
    else:
        print_status("requirements.txt not found in backend directory", "WARNING", Colors.YELLOW)
    
    return python_cmd

def setup_frontend():
    """Set up the frontend environment and install dependencies"""
    print_status("=== Setting up Frontend ===", "INFO", Colors.BLUE)
    frontend_dir = Path("frontend")
    
    # Always run npm install to ensure all dependencies are present
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
                    test_cmd = f'{python_cmd} -c "from pto_scraper import PTOScraper; import json; config=json.load(open(\'config.json\')); scraper=PTOScraper(config[\'pto\']); print(\'Profile test:\', scraper.test_profile())"'
                    result = subprocess.run(test_cmd, shell=True, cwd=backend_dir, capture_output=True, text=True)
                    if "Profile test: True" in result.stdout:
                        print_status("✅ PTO profile is working correctly", "SUCCESS", Colors.GREEN)
                    else:
                        print_status("⚠️ PTO profile exists but test failed - will need setup", "WARNING", Colors.YELLOW)
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
        def log_backend_output():
            while backend_process.poll() is None:
                output = backend_process.stdout.readline()
                if output:
                    output = output.strip()
                    # Only show important messages, filter out verbose logs
                    if any(keyword in output.lower() for keyword in [
                        'error', 'warning', 'critical', 'failed', 'exception',
                        'server ready', 'uvicorn running', 'startup complete',
                        'telegram alerts', 'pto scraper started', 'chrome driver',
                        'cloudflare', 'prop builder', 'setup complete'
                    ]):
                        # Clean up the output for better readability
                        if 'INFO:' in output and 'uvicorn' in output:
                            continue  # Skip uvicorn startup messages
                        if 'Requirement already satisfied' in output:
                            continue  # Skip pip install messages
                        if 'DevTools listening' in output:
                            continue  # Skip Chrome DevTools messages
                        if 'WARNING: All log messages' in output:
                            continue  # Skip Chrome warnings
                        if 'Created TensorFlow' in output:
                            continue  # Skip TensorFlow messages
                        if 'Attempting to use a delegate' in output:
                            continue  # Skip TensorFlow delegate messages
                        if 'USB: usb_service_win.cc' in output:
                            continue  # Skip USB error messages
                        if 'voice_transcription' in output:
                            continue  # Skip voice transcription messages
                        if 'DEP_WEBPACK_DEV_SERVER' in output:
                            continue  # Skip webpack deprecation warnings
                        
                        # Clean up the message
                        if '[Backend]' in output:
                            output = output.replace('[Backend] ', '')
                        
                        # Show only essential messages
                        if any(essential in output for essential in [
                            'Server ready to receive alerts',
                            'PTO scraper started',
                            'Chrome driver created successfully',
                            'Successfully passed Cloudflare challenge',
                            'PTO setup complete',
                            'Telegram alerts configured'
                        ]):
                            print(f"{Colors.BLUE}[Backend]{Colors.RESET} {output}")
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
        def log_frontend_output():
            while frontend_process.poll() is None:
                output = frontend_process.stdout.readline()
                if output:
                    output = output.strip()
                    # Only show important frontend messages
                    if any(keyword in output.lower() for keyword in [
                        'compiled successfully', 'development server', 'localhost',
                        'error', 'warning', 'failed', 'ready'
                    ]):
                        # Skip verbose messages
                        if 'DevTools listening' in output:
                            continue
                        if 'DEP_WEBPACK_DEV_SERVER' in output:
                            continue
                        if 'node:' in output and 'DEP_' in output:
                            continue
                        if 'USB: usb_service_win.cc' in output:
                            continue
                        if 'WARNING: All log messages' in output:
                            continue
                        if 'Created TensorFlow' in output:
                            continue
                        if 'Attempting to use a delegate' in output:
                            continue
                        if 'voice_transcription' in output:
                            continue
                        
                        # Clean up the message
                        if '[Frontend]' in output:
                            output = output.replace('[Frontend] ', '')
                        
                        # Show only essential messages
                        if any(essential in output for essential in [
                            'Starting the development server',
                            'Compiled successfully',
                            'Local:',
                            'On Your Network:',
                            'You can now view'
                        ]):
                            print(f"{Colors.MAGENTA}[Frontend]{Colors.RESET} {output}")
        frontend_log_thread = threading.Thread(target=log_frontend_output, daemon=True)
        frontend_log_thread.start()
        
        # Wait a bit for frontend to start
        time.sleep(5)
        
        # Open browser manually instead of automatically
        def open_browser():
            time.sleep(3)  # Wait a bit more for frontend to be ready
            try:
                frontend_url = f"http://localhost:{frontend_port}"
                print_status(f"Frontend ready at: {frontend_url}", "SUCCESS", Colors.GREEN)
                print_status("Please open this URL in your browser manually", "INFO", Colors.YELLOW)
                # Don't auto-open browser since we set BROWSER=none
                # webbrowser.open(frontend_url)
            except Exception as e:
                print_status(f"Failed to get frontend URL: {e}", "ERROR", Colors.RED)
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Print success banner
        success_banner = f"""
{Colors.GREEN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                🎉 LAUNCH SUCCESSFUL! 🎉                      ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
{Colors.CYAN}📊 Frontend:{Colors.RESET} http://localhost:{frontend_port}
{Colors.CYAN}🔧 Backend API:{Colors.RESET} http://localhost:5001
{Colors.CYAN}📈 Pinnacle Odds Dropper:{Colors.RESET} https://pinnacleoddsdropper.com
{Colors.CYAN}✅ PTO Scraper:{Colors.RESET} Active and running
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