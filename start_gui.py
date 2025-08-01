#!/usr/bin/env python3
"""Quick start script for Nassau Campaign Intelligence GUI."""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path
import requests

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ['streamlit', 'plotly', 'pandas', 'requests']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("📦 Install with: pip install -r requirements-streamlit.txt")
        return False
    
    return True

def start_fastapi():
    """Start FastAPI backend."""
    print("🚀 Starting FastAPI backend...")
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "blackcore.minimal.api.app:app", 
        "--reload", "--port", "8000"
    ])

def wait_for_backend():
    """Wait for backend to be ready."""
    print("⏳ Waiting for backend to start...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ Backend is ready!")
                return True
        except:
            pass
        time.sleep(1)
        print(f"   Still waiting... ({i+1}/30)")
    
    print("❌ Backend failed to start")
    return False

def start_streamlit():
    """Start Streamlit GUI."""
    print("🎨 Starting Streamlit GUI...")
    return subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", 
        "streamlit_app.py", "--server.port", "8501"
    ])

def main():
    """Main startup process."""
    print("🏴‍☠️ Nassau Campaign Intelligence - Quick Start")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("streamlit_app.py").exists():
        print("❌ Please run this script from the blackcore directory")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Start FastAPI
    api_process = start_fastapi()
    
    try:
        # Wait for backend
        if not wait_for_backend():
            api_process.terminate()
            sys.exit(1)
        
        # Start Streamlit
        gui_process = start_streamlit()
        
        # Open browser
        print("🌐 Opening browser...")
        time.sleep(3)  # Give Streamlit time to start
        webbrowser.open("http://localhost:8501")
        
        print("\n" + "=" * 50)
        print("🎯 Nassau Campaign Intelligence is running!")
        print("📊 Dashboard: http://localhost:8501")
        print("🔧 API Docs: http://localhost:8000/docs")
        print("=" * 50)
        print("\n💡 Press Ctrl+C to stop both services")
        
        # Wait for processes
        try:
            gui_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            
    finally:
        # Clean up processes
        try:
            api_process.terminate()
            api_process.wait(timeout=5)
        except:
            api_process.kill()
        
        try:
            gui_process.terminate()
            gui_process.wait(timeout=5)  
        except:
            gui_process.kill()
        
        print("✅ Shutdown complete")

if __name__ == "__main__":
    main()