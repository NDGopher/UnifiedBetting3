#!/usr/bin/env python3
"""
Unified Betting App - Dependency Setup Script
Automatically sets up all required dependencies for both backend and frontend.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import time

def print_status(message, status="INFO"):
    """Print a formatted status message"""
    timestamp = time.strftime("%H:%M:%S")
    status_icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "WARNING": "⚠️",
        "ERROR": "❌",
        "PROGRESS": "🔄"
    }
    icon = status_icons.get(status, "ℹ️")
    print(f"[{timestamp}] {icon} {message}")

def run_command(command, cwd=None, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            timeout=300
        )
        if check and result.returncode != 0:
            print_status(f"Command failed: {command}", "ERROR")
            print_status(f"Error: {result.stderr}", "ERROR")
            return False
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print_status(f"Command timed out: {command}", "ERROR")
        return False
    except Exception as e:
        print_status(f"Command error: {e}", "ERROR")
        return False

def setup_backend():
    """Set up backend dependencies"""
    print_status("=== Setting up Backend ===", "INFO")
    backend_dir = Path("backend")
    
    if not backend_dir.exists():
        print_status("Backend directory not found!", "ERROR")
        return False
    
    # Create virtual environment if it doesn't exist
    venv_path = backend_dir / "venv"
    if not venv_path.exists():
        print_status("Creating virtual environment...", "INFO")
        if not run_command("python -m venv venv", cwd=backend_dir):
            print_status("Failed to create virtual environment", "ERROR")
            return False
        print_status("Virtual environment created successfully", "SUCCESS")
    else:
        print_status("Virtual environment already exists", "SUCCESS")
    
    # Determine Python command based on platform
    if platform.system() == "Windows":
        python_cmd = "venv\\Scripts\\python"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        python_cmd = "venv/bin/python"
        pip_cmd = "venv/bin/pip"
    
    # Check if requirements.txt exists
    requirements_file = backend_dir / "requirements.txt"
    if not requirements_file.exists():
        print_status("requirements.txt not found in backend directory", "WARNING")
        return True
    
    # Check if dependencies are already installed
    print_status("Checking if dependencies are installed...", "INFO")
    try:
        result = subprocess.run(
            f'"{python_cmd}" -c "import uvicorn, fastapi, selenium, requests; print(\'deps_installed\')"',
            shell=True,
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        deps_installed = "deps_installed" in result.stdout
    except:
        deps_installed = False
    
    if deps_installed:
        print_status("Backend dependencies already installed", "SUCCESS")
        return True
    
    # Install dependencies
    print_status("Installing backend dependencies...", "INFO")
    print_status("This may take a few minutes...", "INFO")
    
    # Try to upgrade pip first (but don't fail if it doesn't work)
    print_status("Upgrading pip...", "INFO")
    run_command(f"{python_cmd} -m pip install --upgrade pip", cwd=backend_dir, check=False)
    
    # Install requirements
    print_status("Installing Python packages...", "INFO")
    if not run_command(f"{python_cmd} -m pip install -r requirements.txt", cwd=backend_dir):
        print_status("Failed to install backend requirements", "ERROR")
        print_status("Try running: pip install -r requirements.txt --no-cache-dir", "INFO")
        return False
    
    print_status("Backend dependencies installed successfully", "SUCCESS")
    return True

def setup_frontend():
    """Set up frontend dependencies"""
    print_status("=== Setting up Frontend ===", "INFO")
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        print_status("Frontend directory not found!", "ERROR")
        return False
    
    # Check if package.json exists
    if not (frontend_dir / "package.json").exists():
        print_status("package.json not found in frontend directory", "WARNING")
        return True
    
    # Check if node_modules already exists and key dependencies are installed
    node_modules_exists = (frontend_dir / "node_modules").exists()
    dayjs_exists = (frontend_dir / "node_modules" / "dayjs").exists() if node_modules_exists else False
    
    if node_modules_exists and dayjs_exists:
        print_status("Frontend dependencies already installed", "SUCCESS")
        return True
    
    # Install dependencies
    print_status("Installing frontend dependencies...", "INFO")
    print_status("This may take a few minutes...", "INFO")
    
    # Force clean install to ensure all dependencies are properly installed
    if node_modules_exists:
        print_status("Cleaning existing node_modules for fresh install...", "INFO")
        import shutil
        try:
            shutil.rmtree(frontend_dir / "node_modules")
            print_status("Cleaned existing node_modules", "SUCCESS")
        except Exception as e:
            print_status(f"Warning: Could not clean node_modules: {e}", "WARNING")
    
    # Clean up any conflicting lock files
    bun_lock = frontend_dir / "bun.lock"
    if bun_lock.exists():
        print_status("Cleaning up conflicting Bun lock file...", "INFO")
        try:
            bun_lock.unlink()
            print_status("Removed bun.lock to prevent conflicts", "SUCCESS")
        except Exception as e:
            print_status(f"Warning: Could not remove bun.lock: {e}", "WARNING")
    
    # Install dependencies
    if not run_command("npm install", cwd=frontend_dir):
        print_status("Failed to install frontend dependencies", "ERROR")
        return False
    
    # Verify key dependencies are installed
    if not (frontend_dir / "node_modules" / "dayjs").exists():
        print_status("dayjs not found after install, trying to install it specifically...", "WARNING")
        if not run_command("npm install dayjs", cwd=frontend_dir):
            print_status("Failed to install dayjs dependency", "ERROR")
            return False
    
    print_status("Frontend dependencies installed successfully", "SUCCESS")
    return True

def main():
    """Main setup function"""
    print("🚀 Unified Betting App - Dependency Setup")
    print("=" * 50)
    
    # Get the project directory
    project_dir = Path(__file__).parent.absolute()
    os.chdir(project_dir)
    print_status(f"Project directory: {project_dir}", "INFO")
    
    # Set up backend
    backend_success = setup_backend()
    
    # Set up frontend
    frontend_success = setup_frontend()
    
    # Summary
    print("\n" + "=" * 50)
    if backend_success and frontend_success:
        print_status("🎉 Setup completed successfully!", "SUCCESS")
        print_status("You can now run 'python launch.py' to start the application", "INFO")
    else:
        print_status("⚠️ Setup completed with warnings", "WARNING")
        if not backend_success:
            print_status("Backend setup failed - check the errors above", "ERROR")
        if not frontend_success:
            print_status("Frontend setup failed - check the errors above", "ERROR")
        print_status("Try running the setup again or check your system requirements", "INFO")
    
    return backend_success and frontend_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 