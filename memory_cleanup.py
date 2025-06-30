#!/usr/bin/env python3
"""
Memory Cleanup Script - Reduce high memory usage
"""

import psutil
import os
import time
import subprocess
import platform

def get_memory_usage():
    """Get current memory usage"""
    memory = psutil.virtual_memory()
    return memory.percent, memory.available / (1024**3)

def kill_chrome_processes():
    """Kill all Chrome processes"""
    print("🌐 Killing Chrome processes...")
    killed = 0
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                proc.kill()
                killed += 1
                print(f"  Killed: {proc.info['name']} (PID: {proc.info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if killed > 0:
        print(f"✅ Killed {killed} Chrome processes")
        time.sleep(2)  # Wait for processes to fully terminate
    else:
        print("ℹ️ No Chrome processes found")
    
    return killed

def kill_high_memory_processes():
    """Kill processes using more than 500MB of RAM"""
    print("🔪 Killing high-memory processes (>500MB)...")
    killed = 0
    threshold_mb = 500
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if proc.info['memory_info']:
                memory_mb = proc.info['memory_info'].rss / (1024**2)
                if memory_mb > threshold_mb:
                    # Skip critical system processes
                    if proc.info['name'] not in ['System', 'svchost.exe', 'explorer.exe', 'winlogon.exe']:
                        proc.kill()
                        killed += 1
                        print(f"  Killed: {proc.info['name']} (PID: {proc.info['pid']}) - {memory_mb:.1f} MB")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if killed > 0:
        print(f"✅ Killed {killed} high-memory processes")
        time.sleep(1)
    else:
        print("ℹ️ No high-memory processes found")
    
    return killed

def clear_windows_cache():
    """Clear Windows cache and temporary files"""
    print("🧹 Clearing Windows cache...")
    
    cache_dirs = [
        os.path.expanduser("~\\AppData\\Local\\Temp"),
        os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\INetCache"),
        os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\WebCache"),
        "C:\\Windows\\Temp"
    ]
    
    cleared = 0
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                # Count files before clearing
                file_count = len([f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))])
                
                # Clear files older than 1 day
                current_time = time.time()
                for filename in os.listdir(cache_dir):
                    filepath = os.path.join(cache_dir, filename)
                    try:
                        if os.path.isfile(filepath):
                            if current_time - os.path.getmtime(filepath) > 86400:  # 1 day
                                os.remove(filepath)
                                cleared += 1
                    except (OSError, PermissionError):
                        continue
                
                print(f"  Cleared {cleared} old files from {cache_dir}")
            except Exception as e:
                print(f"  Error clearing {cache_dir}: {e}")
    
    return cleared

def optimize_memory():
    """Optimize memory usage"""
    print("⚡ Optimizing memory...")
    
    # Force garbage collection
    import gc
    gc.collect()
    
    # Clear Python cache
    import sys
    for module in list(sys.modules.keys()):
        if hasattr(sys.modules[module], '__file__'):
            try:
                del sys.modules[module]
            except:
                pass
    
    print("✅ Memory optimization complete")

def restart_critical_services():
    """Restart services that might be consuming memory"""
    print("🔄 Restarting critical services...")
    
    services_to_restart = [
        "wuauserv",  # Windows Update
        "bits",      # Background Intelligent Transfer Service
        "spooler"    # Print Spooler
    ]
    
    for service in services_to_restart:
        try:
            subprocess.run(['net', 'stop', service], capture_output=True, timeout=10)
            time.sleep(2)
            subprocess.run(['net', 'start', service], capture_output=True, timeout=10)
            print(f"  Restarted: {service}")
        except Exception as e:
            print(f"  Could not restart {service}: {e}")

def main():
    """Main cleanup function"""
    print("🧹 MEMORY CLEANUP TOOL")
    print("=" * 50)
    
    # Get initial memory usage
    initial_percent, initial_available = get_memory_usage()
    print(f"📊 Initial memory usage: {initial_percent:.1f}%")
    print(f"📊 Available memory: {initial_available:.1f} GB")
    
    if initial_percent < 80:
        print("ℹ️ Memory usage is acceptable (<80%)")
        response = input("Continue with cleanup anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    print("\n🚀 Starting memory cleanup...")
    
    # Kill Chrome processes
    chrome_killed = kill_chrome_processes()
    
    # Kill high-memory processes
    high_mem_killed = kill_high_memory_processes()
    
    # Clear Windows cache
    cache_cleared = clear_windows_cache()
    
    # Optimize memory
    optimize_memory()
    
    # Restart services (optional)
    response = input("\nRestart Windows services? (y/n): ")
    if response.lower() == 'y':
        restart_critical_services()
    
    # Get final memory usage
    time.sleep(3)  # Wait for cleanup to take effect
    final_percent, final_available = get_memory_usage()
    
    print(f"\n📊 FINAL RESULTS:")
    print("-" * 30)
    print(f"Initial memory usage: {initial_percent:.1f}%")
    print(f"Final memory usage: {final_percent:.1f}%")
    print(f"Memory freed: {initial_percent - final_percent:.1f}%")
    print(f"Available memory: {final_available:.1f} GB")
    
    print(f"\n🧹 CLEANUP SUMMARY:")
    print("-" * 30)
    print(f"Chrome processes killed: {chrome_killed}")
    print(f"High-memory processes killed: {high_mem_killed}")
    print(f"Cache files cleared: {cache_cleared}")
    
    if final_percent < 80:
        print("✅ Memory usage is now acceptable!")
    else:
        print("⚠️ Memory usage is still high. Consider restarting your computer.")
    
    print("\n" + "=" * 50)
    print("🧹 Cleanup complete!")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...") 