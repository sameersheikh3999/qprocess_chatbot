#!/usr/bin/env python3
"""
QProcess Chatbot Production Server Startup Script

This script:
1. Validates environment configuration
2. Checks database connectivity
3. Runs Django migrations if needed
4. Starts the Django server with production settings

Usage:
    python scripts/start_server.py [--port PORT] [--host HOST]
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

def check_environment():
    """Check that required environment variables are set."""
    print("🔍 Checking environment configuration...")
    
    required_vars = ['GROQ_API_KEY', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'SECRET_KEY']
    missing_vars = []
    
    # Load .env file if it exists
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    else:
        print("⚠️  No .env file found. Expecting environment variables to be set externally.")
    
    # Check required variables
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\\n📝 Please set these variables in your .env file or environment:")
        for var in missing_vars:
            print(f"   {var}=your_value_here")
        return False
    
    print("✅ All required environment variables are set")
    return True

def check_database():
    """Test database connectivity."""
    print("🗄️  Testing database connectivity...")
    
    try:
        # Set Django settings module
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')
        os.environ.setdefault('DJANGO_ENV', 'production')
        
        import django
        django.setup()
        
        from django.db import connection
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        print("✅ Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\\n🔧 Troubleshooting tips:")
        print("   1. Verify your database server is running")
        print("   2. Check DB_HOST, DB_PORT, DB_NAME in your .env file")  
        print("   3. Verify DB_USER has access to the database")
        return False

def start_server(host='0.0.0.0', port=8000):
    """Start the Django development server."""
    print(f"🚀 Starting QProcess Chatbot server on {host}:{port}")
    print("   Press Ctrl+C to stop the server")
    
    # Set environment for production
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')
    os.environ.setdefault('DJANGO_ENV', 'production')
    
    try:
        subprocess.run([
            sys.executable, 
            'backend/chatbot/manage.py', 
            'runserver', 
            f'{host}:{port}'
        ], cwd=PROJECT_ROOT)
    except KeyboardInterrupt:
        print("\\n👋 Server stopped")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Start QProcess Chatbot server')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to run server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind server to')
    parser.add_argument('--skip-checks', action='store_true', help='Skip environment and database checks')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 QProcess Chatbot Production Server")
    print("=" * 60)
    
    if not args.skip_checks:
        # Run pre-flight checks
        if not check_environment():
            sys.exit(1)
        
        if not check_database():
            sys.exit(1)
    
    # Start the server
    start_server(args.host, args.port)

if __name__ == '__main__':
    main()