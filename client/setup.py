#!/usr/bin/env python3
"""
Setup script for the Secure Search Test Client
"""
import subprocess
import sys
import os
from pathlib import Path


def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ required, found {sys.version}")
        return False
    
    print(f"✅ Python {sys.version} is compatible")
    return True


def check_server_connection():
    """Check if server is accessible"""
    print("🔌 Checking server connection...")
    
    try:
        import requests
        response = requests.get("http://localhost:8001/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ Server is accessible and healthy")
            return True
        else:
            print(f"⚠️ Server responded with status {response.status_code}")
            return False
            
    except ImportError:
        print("⚠️ Cannot check server (requests not installed yet)")
        return True  # Will check again after installation
    except Exception as e:
        print(f"⚠️ Cannot reach server: {e}")
        print("💡 Make sure Docker containers are running:")
        print("   cd ../")
        print("   docker-compose up -d")
        return False


def main():
    """Run setup checks and installation"""
    print("🚀 Setting up Secure Search Test Client")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
    
    # Install dependencies
    if success and not install_dependencies():
        success = False
    
    # Check server connection
    if success:
        check_server_connection()  # Non-blocking check
    
    print("\n" + "=" * 50)
    
    if success:
        print("✅ Setup completed successfully!")
        print("\n🏃 Ready to run tests:")
        print("   python test_secure_search.py")
    else:
        print("❌ Setup failed!")
        print("\n🔧 Please fix the issues above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()