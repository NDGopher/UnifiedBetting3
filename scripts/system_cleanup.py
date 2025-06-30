#!/usr/bin/env python3
"""
System cleanup script to free up memory and improve performance.
Run this when your system is running slow.
"""

import psutil
import gc
import os
import subprocess
import time

def cleanup_system():
    """Perform system cleanup to free up memory"""
    print("🧹 System Cleanup Starting...")
    print("=" * 50)
    
    # Get initial memory stats
    memory_before = psutil.virtual_memory()
    print(f"Memory before cleanup: {memory_before.percent}% ({memory_before.used / (1024**3):.1f}GB used)")
    
    # 1. Force garbage collection
    print("1. Running garbage collection...")
    collected = gc.collect()
    print(f"   Collected {collected} objects")
    
    # 2. Clear Python cache
    print("2. Clearing Python cache...")
    try:
        import shutil
        cache_dir = os.path.join(os.path.dirname(__file__), '__pycache__')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print("   Cleared __pycache__ directory")
    except Exception as e:
        print(f"   Error clearing cache: {e}")
    
    # 3. Clear browser cache (optional)
    print("3. Browser cache cleanup...")
    try:
        # Clear Chrome cache
        chrome_cache = os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache")
        if os.path.exists(chrome_cache):
            for item in os.listdir(chrome_cache):
                item_path = os.path.join(chrome_cache, item)
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        import shutil
                        shutil.rmtree(item_path)
                except:
                    pass
            print("   Cleared Chrome cache")
    except Exception as e:
        print(f"   Error clearing browser cache: {e}")
    
    # 4. Kill unnecessary processes
    print("4. Checking for unnecessary processes...")
    unnecessary_processes = [
        'chrome.exe', 'msedge.exe', 'firefox.exe',  # Browsers (if too many tabs)
        'discord.exe', 'slack.exe', 'teams.exe',    # Communication apps
        'spotify.exe', 'steam.exe', 'origin.exe'    # Media/gaming apps
    ]
    
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            if proc.info['name'] in unnecessary_processes and proc.info['memory_percent'] > 5:
                print(f"   Found high-memory process: {proc.info['name']} ({proc.info['memory_percent']:.1f}% memory)")
                # Don't actually kill - just warn
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # 5. Restart services if needed
    print("5. Checking betting system services...")
    try:
        import requests
        backend_health = requests.get('http://localhost:5001/test', timeout=5)
        if backend_health.ok:
            print("   Backend is running")
        else:
            print("   Backend may need restart")
    except:
        print("   Backend not accessible")
    
    try:
        frontend_health = requests.get('http://localhost:3000', timeout=5)
        if frontend_health.ok:
            print("   Frontend is running")
        else:
            print("   Frontend may need restart")
    except:
        print("   Frontend not accessible")
    
    # 6. Wait a moment and check memory again
    print("6. Waiting for cleanup to take effect...")
    time.sleep(2)
    
    memory_after = psutil.virtual_memory()
    memory_freed = memory_before.used - memory_after.used
    
    print("\n" + "=" * 50)
    print("🧹 CLEANUP COMPLETE")
    print("=" * 50)
    print(f"Memory after cleanup: {memory_after.percent}% ({memory_after.used / (1024**3):.1f}GB used)")
    print(f"Memory freed: {memory_freed / (1024**3):.1f}GB")
    print(f"Improvement: {memory_before.percent - memory_after.percent:.1f}%")
    
    if memory_after.percent < 80:
        print("✅ Memory usage is now acceptable")
    else:
        print("⚠️  Memory usage is still high - consider:")
        print("   - Closing unnecessary browser tabs")
        print("   - Restarting your computer")
        print("   - Closing other applications")
    
    print("\n💡 Performance Tips:")
    print("- Close unnecessary browser tabs")
    print("- Restart the betting system services if needed")
    print("- Consider restarting your computer if memory usage stays high")
    print("- Monitor with: python performance_monitor.py")

if __name__ == "__main__":
    cleanup_system() 