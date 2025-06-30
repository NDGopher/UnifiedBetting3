#!/usr/bin/env python3
"""
Memory Investigator - Find what's consuming RAM
"""

import psutil
import os
import time
import json
from collections import defaultdict
import subprocess
import platform

def get_memory_info():
    """Get detailed memory information"""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    print("=" * 60)
    print("🧠 MEMORY USAGE ANALYSIS")
    print("=" * 60)
    
    print(f"📊 Total RAM: {memory.total / (1024**3):.1f} GB")
    print(f"📊 Available RAM: {memory.available / (1024**3):.1f} GB")
    print(f"📊 Used RAM: {memory.used / (1024**3):.1f} GB")
    print(f"📊 Memory Usage: {memory.percent:.1f}%")
    print(f"📊 Swap Used: {swap.used / (1024**3):.1f} GB / {swap.total / (1024**3):.1f} GB")
    print(f"📊 Swap Usage: {swap.percent:.1f}%")
    
    return memory

def get_top_processes_by_memory(limit=20):
    """Get top processes by memory usage"""
    print(f"\n🔝 TOP {limit} PROCESSES BY MEMORY USAGE:")
    print("-" * 80)
    
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'status']):
        try:
            proc_info = proc.info
            if proc_info['memory_info']:
                memory_mb = proc_info['memory_info'].rss / (1024**2)
                processes.append({
                    'pid': proc_info['pid'],
                    'name': proc_info['name'],
                    'memory_mb': memory_mb,
                    'cpu_percent': proc_info['cpu_percent'],
                    'status': proc_info['status']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Sort by memory usage
    processes.sort(key=lambda x: x['memory_mb'], reverse=True)
    
    total_memory = sum(p['memory_mb'] for p in processes)
    
    for i, proc in enumerate(processes[:limit]):
        percentage = (proc['memory_mb'] / total_memory) * 100 if total_memory > 0 else 0
        print(f"{i+1:2d}. {proc['name']:<20} | {proc['memory_mb']:8.1f} MB | {percentage:5.1f}% | CPU: {proc['cpu_percent']:5.1f}% | {proc['status']}")
    
    return processes

def check_chrome_processes():
    """Check for Chrome-related processes"""
    print(f"\n🌐 CHROME PROCESSES:")
    print("-" * 40)
    
    chrome_processes = []
    total_chrome_memory = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
        try:
            proc_info = proc.info
            if proc_info['name'] and 'chrome' in proc_info['name'].lower():
                memory_mb = proc_info['memory_info'].rss / (1024**2) if proc_info['memory_info'] else 0
                cmdline = ' '.join(proc_info['cmdline'] or [])
                chrome_processes.append({
                    'pid': proc_info['pid'],
                    'name': proc_info['name'],
                    'memory_mb': memory_mb,
                    'cmdline': cmdline
                })
                total_chrome_memory += memory_mb
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if chrome_processes:
        print(f"Found {len(chrome_processes)} Chrome processes:")
        for proc in chrome_processes:
            print(f"  PID {proc['pid']}: {proc['name']} - {proc['memory_mb']:.1f} MB")
        print(f"Total Chrome memory: {total_chrome_memory:.1f} MB")
    else:
        print("No Chrome processes found")
    
    return chrome_processes

def check_python_processes():
    """Check for Python processes"""
    print(f"\n🐍 PYTHON PROCESSES:")
    print("-" * 40)
    
    python_processes = []
    total_python_memory = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
        try:
            proc_info = proc.info
            if proc_info['name'] and 'python' in proc_info['name'].lower():
                memory_mb = proc_info['memory_info'].rss / (1024**2) if proc_info['memory_info'] else 0
                cmdline = ' '.join(proc_info['cmdline'] or [])
                python_processes.append({
                    'pid': proc_info['pid'],
                    'name': proc_info['name'],
                    'memory_mb': memory_mb,
                    'cmdline': cmdline
                })
                total_python_memory += memory_mb
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if python_processes:
        print(f"Found {len(python_processes)} Python processes:")
        for proc in python_processes:
            print(f"  PID {proc['pid']}: {proc['name']} - {proc['memory_mb']:.1f} MB")
            if 'unifiedbetting' in proc['cmdline'].lower():
                print(f"    CMD: {proc['cmdline'][:100]}...")
        print(f"Total Python memory: {total_python_memory:.1f} MB")
    else:
        print("No Python processes found")
    
    return python_processes

def check_node_processes():
    """Check for Node.js processes"""
    print(f"\n🟢 NODE.JS PROCESSES:")
    print("-" * 40)
    
    node_processes = []
    total_node_memory = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
        try:
            proc_info = proc.info
            if proc_info['name'] and 'node' in proc_info['name'].lower():
                memory_mb = proc_info['memory_info'].rss / (1024**2) if proc_info['memory_info'] else 0
                cmdline = ' '.join(proc_info['cmdline'] or [])
                node_processes.append({
                    'pid': proc_info['pid'],
                    'name': proc_info['name'],
                    'memory_mb': memory_mb,
                    'cmdline': cmdline
                })
                total_node_memory += memory_mb
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if node_processes:
        print(f"Found {len(node_processes)} Node.js processes:")
        for proc in node_processes:
            print(f"  PID {proc['pid']}: {proc['name']} - {proc['memory_mb']:.1f} MB")
        print(f"Total Node.js memory: {total_node_memory:.1f} MB")
    else:
        print("No Node.js processes found")
    
    return node_processes

def check_system_memory():
    """Check system memory details"""
    print(f"\n💻 SYSTEM MEMORY DETAILS:")
    print("-" * 40)
    
    # Get memory by category
    memory = psutil.virtual_memory()
    
    # Calculate memory by type
    cached = getattr(memory, 'cached', 0) / (1024**3)
    buffers = getattr(memory, 'buffers', 0) / (1024**3)
    shared = getattr(memory, 'shared', 0) / (1024**3)
    
    print(f"📊 Cached: {cached:.1f} GB")
    print(f"📊 Buffers: {buffers:.1f} GB")
    print(f"📊 Shared: {shared:.1f} GB")
    
    # Check for memory leaks
    if memory.percent > 90:
        print(f"⚠️  HIGH MEMORY USAGE DETECTED: {memory.percent:.1f}%")
        print("🔍 This could indicate:")
        print("   - Memory leaks in applications")
        print("   - Too many browser tabs/windows")
        print("   - Background services consuming RAM")
        print("   - System cache not being cleared")

def suggest_cleanup():
    """Suggest cleanup actions"""
    print(f"\n🧹 MEMORY CLEANUP SUGGESTIONS:")
    print("-" * 40)
    
    memory = psutil.virtual_memory()
    
    if memory.percent > 90:
        print("🚨 CRITICAL: Memory usage is very high!")
        print("\nImmediate actions:")
        print("1. Close unnecessary applications")
        print("2. Restart your computer")
        print("3. Check for memory leaks in running programs")
    
    print("\nGeneral cleanup:")
    print("1. Close unused browser tabs")
    print("2. End unnecessary background processes")
    print("3. Clear browser cache and cookies")
    print("4. Restart applications that use a lot of memory")
    print("5. Check Windows Task Manager for high-memory processes")

def main():
    """Main investigation function"""
    print("🔍 MEMORY INVESTIGATOR")
    print("=" * 60)
    
    # Get overall memory info
    memory = get_memory_info()
    
    # Check specific process types
    chrome_procs = check_chrome_processes()
    python_procs = check_python_processes()
    node_procs = check_node_processes()
    
    # Get top processes
    top_processes = get_top_processes_by_memory(15)
    
    # Check system memory details
    check_system_memory()
    
    # Calculate totals
    total_chrome = sum(p['memory_mb'] for p in chrome_procs)
    total_python = sum(p['memory_mb'] for p in python_procs)
    total_node = sum(p['memory_mb'] for p in node_procs)
    total_top = sum(p['memory_mb'] for p in top_processes[:10])
    
    print(f"\n📈 MEMORY SUMMARY:")
    print("-" * 40)
    print(f"Chrome processes: {total_chrome:.1f} MB")
    print(f"Python processes: {total_python:.1f} MB")
    print(f"Node.js processes: {total_node:.1f} MB")
    print(f"Top 10 processes: {total_top:.1f} MB")
    print(f"Total system memory: {memory.total / (1024**3):.1f} GB")
    print(f"Available memory: {memory.available / (1024**3):.1f} GB")
    
    # Suggest cleanup
    suggest_cleanup()
    
    print(f"\n" + "=" * 60)
    print("🔍 Investigation complete!")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...") 