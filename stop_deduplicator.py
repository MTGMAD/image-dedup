#!/usr/bin/env python3
"""
Script to stop any running Image Deduplicator processes
"""

import os
import sys
import signal
import psutil

def find_deduplicator_processes():
    """Find running Image Deduplicator processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'image_deduplicator.py' in cmdline:
                    processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def stop_processes():
    """Stop all Image Deduplicator processes."""
    processes = find_deduplicator_processes()
    
    if not processes:
        print("No Image Deduplicator processes found.")
        return
    
    print(f"Found {len(processes)} Image Deduplicator process(es):")
    
    for proc in processes:
        try:
            print(f"  PID {proc.pid}: {' '.join(proc.cmdline())}")
            
            # Try graceful termination first
            proc.terminate()
            
            # Wait a bit for graceful shutdown
            try:
                proc.wait(timeout=5)
                print(f"  Process {proc.pid} terminated gracefully.")
            except psutil.TimeoutExpired:
                # Force kill if it doesn't terminate
                proc.kill()
                print(f"  Process {proc.pid} force killed.")
                
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"  Could not stop process {proc.pid}: {e}")
    
    print("Done.")

if __name__ == "__main__":
    try:
        stop_processes()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
