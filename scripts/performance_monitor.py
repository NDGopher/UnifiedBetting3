#!/usr/bin/env python3
"""
Performance monitoring script for the betting system.
Checks CPU, memory, and network usage to identify bottlenecks.
"""

import psutil
import time
import requests
import json
from datetime import datetime
import threading

class PerformanceMonitor:
    def __init__(self):
        self.monitoring = False
        self.stats_history = []
        
    def get_system_stats(self):
        """Get current system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network stats
            net_io = psutil.net_io_counters()
            
            # Get process stats for Python processes
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if 'python' in proc.info['name'].lower():
                        python_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'network_bytes_sent': net_io.bytes_sent,
                'network_bytes_recv': net_io.bytes_recv,
                'python_processes': python_processes
            }
        except Exception as e:
            print(f"Error getting system stats: {e}")
            return None
    
    def check_backend_health(self):
        """Check backend API health and response time"""
        try:
            start_time = time.time()
            response = requests.get('http://localhost:5001/test', timeout=5)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'status': 'healthy' if response.ok else 'unhealthy',
                'response_time_ms': round(response_time, 2),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'response_time_ms': None,
                'error': str(e)
            }
    
    def check_frontend_health(self):
        """Check frontend health and response time"""
        try:
            start_time = time.time()
            response = requests.get('http://localhost:3000', timeout=5)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'status': 'healthy' if response.ok else 'unhealthy',
                'response_time_ms': round(response_time, 2),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'response_time_ms': None,
                'error': str(e)
            }
    
    def get_backend_stats(self):
        """Get backend-specific statistics if available"""
        try:
            response = requests.get('http://localhost:5001/stats', timeout=5)
            if response.ok:
                return response.json()
            return None
        except:
            return None
    
    def monitor_performance(self, duration_seconds=60, interval_seconds=5):
        """Monitor performance for a specified duration"""
        print(f"🔍 Starting performance monitoring for {duration_seconds} seconds...")
        print("=" * 60)
        
        self.monitoring = True
        start_time = time.time()
        
        while self.monitoring and (time.time() - start_time) < duration_seconds:
            # Get system stats
            system_stats = self.get_system_stats()
            if system_stats:
                self.stats_history.append(system_stats)
            
            # Get service health
            backend_health = self.check_backend_health()
            frontend_health = self.check_frontend_health()
            backend_stats = self.get_backend_stats()
            
            # Print current status
            print(f"\n📊 {datetime.now().strftime('%H:%M:%S')} - Performance Snapshot:")
            print(f"   CPU: {system_stats['cpu_percent']}% | Memory: {system_stats['memory_percent']}% ({system_stats['memory_used_gb']}GB used)")
            print(f"   Backend: {backend_health['status']} ({backend_health.get('response_time_ms', 'N/A')}ms)")
            print(f"   Frontend: {frontend_health['status']} ({frontend_health.get('response_time_ms', 'N/A')}ms)")
            
            # Check for high CPU processes
            high_cpu_processes = [p for p in system_stats['python_processes'] if p['cpu_percent'] > 10]
            if high_cpu_processes:
                print("   ⚠️  High CPU Python processes:")
                for proc in high_cpu_processes:
                    print(f"      PID {proc['pid']}: {proc['cpu_percent']}% CPU, {proc['memory_percent']}% Memory")
            
            # Check for memory issues
            if system_stats['memory_percent'] > 80:
                print("   ⚠️  High memory usage detected!")
            
            if system_stats['cpu_percent'] > 80:
                print("   ⚠️  High CPU usage detected!")
            
            time.sleep(interval_seconds)
        
        self.monitoring = False
        self.print_summary()
    
    def print_summary(self):
        """Print performance summary"""
        if not self.stats_history:
            print("No performance data collected.")
            return
        
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        # Calculate averages
        cpu_values = [s['cpu_percent'] for s in self.stats_history]
        memory_values = [s['memory_percent'] for s in self.stats_history]
        
        avg_cpu = sum(cpu_values) / len(cpu_values)
        max_cpu = max(cpu_values)
        avg_memory = sum(memory_values) / len(memory_values)
        max_memory = max(memory_values)
        
        print(f"CPU Usage: Avg {avg_cpu:.1f}% | Max {max_cpu:.1f}%")
        print(f"Memory Usage: Avg {avg_memory:.1f}% | Max {max_memory:.1f}%")
        
        # Identify potential issues
        if avg_cpu > 50:
            print("⚠️  High average CPU usage detected")
        if max_cpu > 80:
            print("⚠️  CPU spikes detected")
        if avg_memory > 70:
            print("⚠️  High average memory usage detected")
        if max_memory > 90:
            print("⚠️  Memory spikes detected")
        
        # Network usage
        if len(self.stats_history) > 1:
            first_net = self.stats_history[0]
            last_net = self.stats_history[-1]
            bytes_sent = last_net['network_bytes_sent'] - first_net['network_bytes_sent']
            bytes_recv = last_net['network_bytes_recv'] - first_net['network_bytes_recv']
            
            print(f"Network Activity: {bytes_sent/1024:.1f}KB sent, {bytes_recv/1024:.1f}KB received")
        
        print("\n💡 Recommendations:")
        if avg_cpu > 50:
            print("- Consider reducing polling intervals")
            print("- Check for infinite loops or heavy computations")
        if avg_memory > 70:
            print("- Check for memory leaks in event processing")
            print("- Consider reducing the number of concurrent events")
        if max_cpu > 80 or max_memory > 90:
            print("- System may be under heavy load")
            print("- Consider restarting services if issues persist")

def main():
    monitor = PerformanceMonitor()
    
    print("🔍 Betting System Performance Monitor")
    print("=" * 50)
    print("This will monitor your system for 60 seconds to identify performance issues.")
    print("Press Ctrl+C to stop early.")
    
    try:
        monitor.monitor_performance(duration_seconds=60, interval_seconds=5)
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        monitor.monitoring = False
        monitor.print_summary()

if __name__ == "__main__":
    main() 