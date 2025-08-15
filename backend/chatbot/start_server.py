#!/usr/bin/env python3
"""
Django Server Startup Script
Ensures environment is properly configured before starting the server
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def check_environment():
    """Check if required environment variables are set"""
    # Load .env file
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
    
    # Check for required environment variables
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("\n❌ ERROR: CLAUDE_API_KEY not found in environment!")
        print("\nPlease ensure your .env file contains:")
        print("CLAUDE_API_KEY=your-api-key-here")
        print("\nOr set it in your environment:")
        print("export CLAUDE_API_KEY='your-api-key-here'")
        return False
    
    print("✓ CLAUDE_API_KEY found in environment")
    print(f"✓ API Key: {api_key[:20]}...{api_key[-4:]}")  # Show partial key for verification
    return True

def start_server(port=8000):
    """Start the Django development server"""
    print(f"\n🚀 Starting Django server on port {port}...")
    
    # Use the current Python interpreter
    python_exe = sys.executable
    
    # Start the server
    try:
        subprocess.run([
            python_exe, 
            'manage.py', 
            'runserver', 
            f'0.0.0.0:{port}'
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    print("="*60)
    print("QProcess Chatbot Django Server")
    print("="*60)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Parse port from command line if provided
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"⚠️  Invalid port: {sys.argv[1]}, using default 8000")
    
    # Start server
    start_server(port)

if __name__ == "__main__":
    main()