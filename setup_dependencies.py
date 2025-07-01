#!/usr/bin/env python3
"""
Standalone dependency installer for Unified Betting App
Run this script if you encounter issues with the main launch script
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_status(message, status="INFO"):
    """Print a formatted status message"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{status}] {message}")

def setup_backend_dependencies():
    """Set up backend dependencies manually"""
    print_status("=== Manual Backend Dependency Setup ===", "INFO")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print_status("Backend directory not found!", "ERROR")
        return False
    
    # Check if virtual environment exists
    venv_dir = backend_dir / "venv"
    if not venv_dir.exists():
        print_status("Creating virtual environment...", "INFO")
        result = subprocess.run("python -m venv venv", shell=True, cwd=backend_dir)
        if result.returncode != 0:
            print_status("Failed to create virtual environment", "ERROR")
            return False
    
    # Determine Python command
    if sys.platform == "win32":
        python_cmd = "venv\\Scripts\\python"
    else:
        python_cmd = "venv/bin/python"
    
    # Upgrade pip
    print_status("Upgrading pip...", "INFO")
    result = subprocess.run(f"{python_cmd} -m pip install --upgrade pip", shell=True, cwd=backend_dir)
    if result.returncode != 0:
        print_status("Failed to upgrade pip", "ERROR")
        return False
    
    # Install requirements
    requirements_file = backend_dir / "requirements.txt"
    if not requirements_file.exists():
        print_status("requirements.txt not found!", "ERROR")
        return False
    
    print_status("Installing Python packages (this may take several minutes)...", "INFO")
    print_status("💡 You'll see download progress below...", "INFO")
    
    result = subprocess.run(f"{python_cmd} -m pip install -r requirements.txt", shell=True, cwd=backend_dir)
    if result.returncode != 0:
        print_status("Failed to install requirements", "ERROR")
        print_status("💡 Try running: pip install -r requirements.txt --no-cache-dir", "INFO")
        return False
    
    print_status("✅ Backend dependencies installed successfully!", "SUCCESS")
    return True

def setup_frontend_dependencies():
    """Set up frontend dependencies manually"""
    print_status("=== Manual Frontend Dependency Setup ===", "INFO")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print_status("Frontend directory not found!", "ERROR")
        return False
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists():
        print_status("Frontend dependencies already installed", "INFO")
        return True
    
    print_status("Installing Node.js dependencies...", "INFO")
    result = subprocess.run("npm install", shell=True, cwd=frontend_dir)
    if result.returncode != 0:
        print_status("Failed to install frontend dependencies", "ERROR")
        return False
    
    print_status("✅ Frontend dependencies installed successfully!", "SUCCESS")
    return True

def main():
    """Main setup function"""
    print("🚀 Unified Betting App - Manual Dependency Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("launch.py").exists():
        print_status("Please run this script from the project root directory", "ERROR")
        return False
    
    # Setup backend
    if not setup_backend_dependencies():
        return False
    
    # Setup frontend
    if not setup_frontend_dependencies():
        return False
    
    print_status("🎉 All dependencies installed successfully!", "SUCCESS")
    print_status("You can now run 'python launch.py' to start the application", "INFO")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 