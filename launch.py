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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        logger.info("psutil not found, attempting to install...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import psutil
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections():
                if conn.laddr.port == port:
                    logger.info(f"Killing process on port {port}")
                    proc.kill()
                    time.sleep(0.5)  # Reduced wait time
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def run_command(command, cwd=None, silent=False):
    """Run a command and print its output in real-time"""
    logger.info(f"Running command: {command}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE if silent else None,
        stderr=subprocess.STDOUT if silent else None,
        text=True,
        shell=True,
        cwd=cwd
    )
    
    if not silent:
        process.wait()
        if process.returncode != 0:
            logger.error(f"Command failed with return code {process.returncode}")
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
                print(f"Removing problematic file: {file_path}")
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")

def setup_pto_profile(backend_dir, python_cmd):
    """Setup PTO Chrome profile if needed"""
    logger.info("\n=== Checking PTO Chrome Profile ===")
    
    config_path = backend_dir / "config.json"
    if not config_path.exists():
        logger.warning("config.json not found, PTO setup will be needed")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        pto_config = config.get("pto", {})
        profile_dir = pto_config.get("chrome_user_data_dir")
        
        # Check if profile already exists and is working
        if profile_dir and os.path.exists(profile_dir):
            logger.info("PTO profile directory exists, testing...")
            test_cmd = f'{python_cmd} -c "from pto_scraper import PTOScraper; import json; config=json.load(open(\'config.json\')); scraper=PTOScraper(config[\'pto\']); print(\'Profile test:\', scraper.test_profile())"'
            result = subprocess.run(test_cmd, shell=True, cwd=backend_dir, capture_output=True, text=True)
            if "Profile test: True" in result.stdout:
                logger.info("✅ PTO profile is working correctly")
                return True
            else:
                logger.warning("⚠️ PTO profile exists but test failed")
                logger.info("💡 You can run 'python setup_pto_profile.py' in the backend directory to fix this")
                return False
        else:
            logger.info("ℹ️ PTO profile not found")
            logger.info("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up")
            return False
            
    except Exception as e:
        logger.error(f"Error checking PTO profile: {e}")
        logger.info("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up")
        return False

def open_pinnacle_odds_dropper():
    """Open pinnacleoddsdropper.com in default browser"""
    logger.info("\n=== Opening Pinnacle Odds Dropper ===")
    try:
        url = "https://pinnacleoddsdropper.com"
        logger.info(f"Opening {url} in default browser...")
        webbrowser.open(url)
        logger.info("✅ Pinnacle Odds Dropper opened successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to open Pinnacle Odds Dropper: {e}")
        return False

def refresh_pinnacle_odds_dropper():
    """Refresh the Pinnacle Odds Dropper tab to ensure Chrome extension is working"""
    logger.info("\n=== Refreshing Pinnacle Odds Dropper ===")
    try:
        url = "https://pinnacleoddsdropper.com"
        logger.info(f"Refreshing {url} in existing browser window...")
        webbrowser.open(url, new=1)  # new=1 refreshes existing window
        logger.info("✅ Pinnacle Odds Dropper refreshed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh Pinnacle Odds Dropper: {e}")
        return False

def setup_backend():
    """Set up the backend environment and install dependencies"""
    logger.info("\n=== Setting up Backend ===")
    backend_dir = Path("backend")
    
    # Create virtual environment if it doesn't exist
    if not (backend_dir / "venv").exists():
        logger.info("Creating virtual environment...")
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
        logger.info("Installing backend dependencies...")
        # First upgrade pip to avoid warnings
        if run_command(f"{python_cmd} -m pip install --upgrade pip", cwd=backend_dir).wait() != 0:
            raise Exception("Failed to upgrade pip")
        
        # Then install requirements
        if run_command(f"{python_cmd} -m pip install -r requirements.txt", cwd=backend_dir).wait() != 0:
            raise Exception("Failed to install backend requirements")
    else:
        logger.warning("requirements.txt not found in backend directory")
    
    return python_cmd

def setup_frontend():
    """Set up the frontend environment and install dependencies"""
    logger.info("\n=== Setting up Frontend ===")
    frontend_dir = Path("frontend")
    
    # Always run npm install to ensure all dependencies are present
    logger.info("Installing frontend dependencies...")
    if run_command("npm install", cwd=frontend_dir, silent=True).wait() != 0:
        raise Exception("Failed to install frontend dependencies")

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
    try:
        logger.info("\n=== Launching Unified Betting Application ===")
        # Get the absolute path to the project directory
        project_dir = Path(__file__).parent.absolute()
        os.chdir(project_dir)
        logger.info(f"Project directory: {project_dir}")
        # Check for problematic files
        check_for_problematic_files(project_dir)
        
        # Check PTO profile automatically without prompting
        backend_dir = project_dir / "backend"
        python_cmd = sys.executable
        
        # Check if PTO profile exists and is working
        config_path = backend_dir / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                pto_config = config.get("pto", {})
                profile_dir = pto_config.get("chrome_user_data_dir")
                
                if profile_dir and os.path.exists(profile_dir):
                    logger.info("PTO profile directory exists, testing...")
                    test_cmd = f'{python_cmd} -c "from pto_scraper import PTOScraper; import json; config=json.load(open(\'config.json\')); scraper=PTOScraper(config[\'pto\']); print(\'Profile test:\', scraper.test_profile())"'
                    result = subprocess.run(test_cmd, shell=True, cwd=backend_dir, capture_output=True, text=True)
                    if "Profile test: True" in result.stdout:
                        logger.info("✅ PTO profile is working correctly")
                    else:
                        logger.warning("⚠️ PTO profile exists but test failed - will need setup")
                        logger.info("💡 You can run 'python setup_pto_profile.py' in the backend directory to fix this")
                else:
                    logger.info("ℹ️ PTO profile not found - will need setup")
                    logger.info("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up")
            except Exception as e:
                logger.error(f"Error checking PTO profile: {e}")
                logger.info("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up")
        else:
            logger.warning("config.json not found, PTO setup will be needed")
            logger.info("💡 You can run 'python setup_pto_profile.py' in the backend directory to set it up")
        
        # Continue with the rest of the launch sequence
        # Kill any existing processes on ports 3000-3010 and 5001
        logger.info("Checking for existing processes...")
        for port in range(3000, 3011):
            kill_process_on_port(port)
        kill_process_on_port(5001)
        # Find free ports
        frontend_port = find_free_port(3000, 3010)
        if not frontend_port:
            raise Exception("Could not find a free port for the frontend")
        logger.info(f"Using frontend port: {frontend_port}")
        # Always set up environments to ensure dependencies are installed
        python_cmd = setup_backend()
        setup_frontend()
        # Open Pinnacle Odds Dropper
        open_pinnacle_odds_dropper()
        # Launch backend server
        logger.info("\n=== Starting Backend (FastAPI/Uvicorn) on port 5001 ===")
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
        # Log backend output in a separate thread
        def log_backend_output():
            while backend_process.poll() is None:
                output = backend_process.stdout.readline()
                if output:
                    print(f"[Backend] {output.strip()}")
        backend_log_thread = threading.Thread(target=log_backend_output, daemon=True)
        backend_log_thread.start()
        # Wait for backend to be ready
        logger.info("Waiting for backend to start...")
        if not wait_for_backend(5001, 30):
            logger.error("Backend failed to start within 30 seconds")
            backend_process.terminate()
            raise Exception("Backend startup timeout")
        logger.info("✅ Backend is ready!")
        # Launch frontend server
        frontend_dir = project_dir / "frontend"
        logger.info(f"\n=== Starting Frontend (React) on port {frontend_port} ===")
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
        # Log frontend output in a separate thread
        def log_frontend_output():
            while frontend_process.poll() is None:
                output = frontend_process.stdout.readline()
                if output:
                    print(f"[Frontend] {output.strip()}")
        frontend_log_thread = threading.Thread(target=log_frontend_output, daemon=True)
        frontend_log_thread.start()
        # Wait a bit for frontend to start
        time.sleep(5)
        # Open browser manually instead of automatically
        def open_browser():
            time.sleep(3)  # Wait a bit more for frontend to be ready
            try:
                frontend_url = f"http://localhost:{frontend_port}"
                logger.info(f"Frontend ready at: {frontend_url}")
                logger.info("Please open this URL in your browser manually")
                # Don't auto-open browser since we set BROWSER=none
                # webbrowser.open(frontend_url)
            except Exception as e:
                logger.error(f"Failed to get frontend URL: {e}")
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        logger.info("\n" + "="*60)
        logger.info("🎉 UNIFIED BETTING APP LAUNCHED SUCCESSFULLY!")
        logger.info("="*60)
        logger.info(f"📊 Frontend: http://localhost:{frontend_port}")
        logger.info("🔧 Backend API: http://localhost:5001")
        logger.info("📈 Pinnacle Odds Dropper: https://pinnacleoddsdropper.com")
        logger.info("✅ PTO Scraper: Active and running")
        logger.info("="*60)
        logger.info("Press Ctrl+C to stop all services")
        logger.info("="*60)
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
                if backend_process.poll() is not None:
                    logger.error("Backend process died unexpectedly")
                    break
                if frontend_process.poll() is not None:
                    logger.error("Frontend process died unexpectedly")
                    break
        except KeyboardInterrupt:
            logger.info("\nShutting down services...")
            backend_process.terminate()
            frontend_process.terminate()
            logger.info("Services stopped")
    except Exception as e:
        logger.error(f"Failed to launch application: {e}")
        raise

if __name__ == "__main__":
    launch_application() 