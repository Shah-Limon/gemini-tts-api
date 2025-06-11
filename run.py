#!/usr/bin/env python3
"""
Gemini TTS API Development Server Runner
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_requirements():
    """Check if all required packages are installed"""
    required_packages = ['flask', 'flask_cors', 'google.genai', 'dotenv']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install them with:")
        print("   pip install -r requirements.txt")
        return False
    return True

def check_api_key():
    """Check if API key is configured"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found!")
        print("\n💡 Create a .env file with:")
        print("   GEMINI_API_KEY=your_actual_api_key_here")
        print("\n   Or set it as environment variable:")
        print("   export GEMINI_API_KEY=your_actual_api_key_here")
        return False
    
    print(f"✅ API Key configured: {api_key[:10]}...{api_key[-4:]}")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ['static', 'uploads', 'temp']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")

def main():
    """Main function to run the development server"""
    print("🔍 Checking requirements...")
    
    if not check_requirements():
        sys.exit(1)
    
    if not check_api_key():
        sys.exit(1)
    
    create_directories()
    
    # Import and run the Flask app
    try:
        from app import app
        
        # Configuration
        port = int(os.environ.get("PORT", 5000))
        debug = os.environ.get("FLASK_ENV", "development") == "development"
        host = os.environ.get("HOST", "0.0.0.0")
        
        print("\n" + "="*60)
        print("🚀 GEMINI TTS API SERVER")
        print("="*60)
        print(f"📍 Server URL:    http://localhost:{port}")
        print(f"🌐 Frontend URL:  http://localhost:{port}/static/index.html")
        print(f"🔍 Health Check:  http://localhost:{port}/health")
        print(f"📚 API Endpoint:  http://localhost:{port}/api/text-to-speech")
        print("="*60)
        print(f"🔧 Debug Mode:    {debug}")
        print(f"🌍 Host:          {host}")
        print(f"🚪 Port:          {port}")
        print("="*60)
        print("\n💡 Tips:")
        print("   - Place your HTML frontend in the 'static/' directory")
        print("   - Use Ctrl+C to stop the server")
        print("   - Server will auto-reload when you modify files (debug mode)")
        print("\n🚀 Starting server...\n")
        
        # Run the Flask application
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            threaded=True
        )
        
    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()