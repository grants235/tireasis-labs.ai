#!/usr/bin/env python3
"""
Simple SSH tunnel manager for PostgreSQL database connection to Azure VM.
"""

import subprocess
import sys
import os

# Configuration
VM_IP = "172.173.216.20"
VM_USER = "azureuser"
SSH_KEY_PATH = os.path.expanduser("~/.ssh/azure_vm_key")
LOCAL_PORT = 5432
REMOTE_PORT = 5432


def is_tunnel_running():
    """Check if SSH tunnel is already running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"ssh.*{LOCAL_PORT}.*{VM_USER}@{VM_IP}"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def start_tunnel():
    """Start the SSH tunnel."""
    if is_tunnel_running():
        print(f"SSH tunnel is already running on port {LOCAL_PORT}")
        return True
    
    print(f"Starting SSH tunnel to {VM_USER}@{VM_IP}...")
    
    try:
        subprocess.run([
            "ssh",
            "-i", SSH_KEY_PATH,
            "-o", "StrictHostKeyChecking=no",
            "-L", f"{LOCAL_PORT}:localhost:{REMOTE_PORT}",
            "-N", "-f",
            f"{VM_USER}@{VM_IP}"
        ], check=True)
        
        print(f"✅ SSH tunnel started! PostgreSQL is now accessible at localhost:{LOCAL_PORT}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start SSH tunnel: {e}")
        return False


def stop_tunnel():
    """Stop the SSH tunnel."""
    if not is_tunnel_running():
        print("No SSH tunnel is currently running")
        return True
    
    print("Stopping SSH tunnel...")
    
    try:
        subprocess.run([
            "pkill", "-f", f"ssh.*{LOCAL_PORT}.*{VM_USER}@{VM_IP}"
        ], check=True)
        
        print("✅ SSH tunnel stopped")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to stop SSH tunnel: {e}")
        return False


def status():
    """Show tunnel status."""
    if is_tunnel_running():
        print(f"✅ SSH tunnel is running - PostgreSQL accessible at localhost:{LOCAL_PORT}")
    else:
        print("❌ SSH tunnel is not running")


def main():
    if len(sys.argv) != 2:
        print("Usage: python ssh_tunnel.py [start|stop|status]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        start_tunnel()
    elif command == "stop":
        stop_tunnel()
    elif command == "status":
        status()
    else:
        print("Invalid command. Use: start, stop, or status")
        sys.exit(1)


if __name__ == "__main__":
    main()