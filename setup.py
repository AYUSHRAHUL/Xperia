#!/usr/bin/env python3
"""
Urban Pulse Setup Script
Helps initialize the application with proper configuration
"""

import os
import sys
from pathlib import Path


def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_file.exists():
        print("✓ .env file already exists")
        return
    
    if not env_example.exists():
        print("✗ .env.example not found")
        return
    
    # Copy .env.example to .env
    with open(env_example, 'r') as f:
        content = f.read()
    
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✓ Created .env file from .env.example")
    print("  Please update the values in .env with your actual configuration")


def check_python_version():
    """Check if Python version is 3.8+"""
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def check_venv():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("⚠ Warning: Not running in a virtual environment")
        print("  It's recommended to create and activate a virtual environment:")
        print("  python -m venv venv")
        print("  .\\venv\\Scripts\\activate  (Windows)")
        print("  source venv/bin/activate  (Linux/Mac)")
        return False
    
    print("✓ Running in virtual environment")
    return True


def install_dependencies():
    """Install Python dependencies"""
    import subprocess
    
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("✗ Failed to install dependencies")
        sys.exit(1)


def check_mongodb():
    """Check if MongoDB connection string is configured"""
    from dotenv import load_dotenv
    load_dotenv()
    
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri or mongo_uri == 'mongodb://localhost:27017':
        print("\n⚠ MongoDB Configuration:")
        print("  Using local MongoDB (mongodb://localhost:27017)")
        print("  Make sure MongoDB is running locally, or")
        print("  Update MONGO_URI in .env with your MongoDB Atlas connection string")
    else:
        print("✓ MongoDB URI configured")


def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("Setup Complete! Next Steps:")
    print("="*60)
    print("\n1. Update .env file with your configuration:")
    print("   - Set SECRET_KEY and JWT_SECRET to secure random strings")
    print("   - Configure MONGO_URI (MongoDB Atlas or local)")
    print("   - Add CLOUDINARY_URL for image uploads (optional)")
    print("   - Add GOOGLE_MAPS_API_KEY for map features (optional)")
    print("\n2. Seed the database with demo data (optional):")
    print("   python seed.py")
    print("\n3. Run the application:")
    print("   python run.py")
    print("\n4. Access the application:")
    print("   http://localhost:5000")
    print("\n5. Demo accounts (after seeding):")
    print("   Admin:  admin@urbanpulse.local / admin123")
    print("   Worker: worker@urbanpulse.local / worker123")
    print("   Citizen: citizen@urbanpulse.local / citizen123")
    print("\n" + "="*60)


def main():
    print("="*60)
    print("Urban Pulse - Setup Script")
    print("="*60)
    print()
    
    # Check Python version
    check_python_version()
    
    # Check virtual environment
    check_venv()
    
    # Create .env file
    create_env_file()
    
    # Install dependencies
    response = input("\nInstall dependencies from requirements.txt? (y/n): ")
    if response.lower() in ['y', 'yes']:
        install_dependencies()
    
    # Check MongoDB configuration
    check_mongodb()
    
    # Print next steps
    print_next_steps()


if __name__ == '__main__':
    main()
