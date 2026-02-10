"""
Quick MongoDB Connection Test
Run this to check if MongoDB is properly configured
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient

def test_connection():
    load_dotenv()
    
    print("\n" + "="*70)
    print("🔍 TESTING MONGODB CONNECTION")
    print("="*70 + "\n")
    
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "urban_pulse")
    
    print(f"📍 MongoDB URI: {mongo_uri}")
    print(f"📦 Database Name: {db_name}\n")
    
    try:
        print("⏳ Connecting to MongoDB...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!\n")
        
        # Check database
        db = client[db_name]
        user_count = db.users.count_documents({})
        issue_count = db.issues.count_documents({})
        
        print(f"📊 Database Status:")
        print(f"   Users: {user_count}")
        print(f"   Issues: {issue_count}\n")
        
        if user_count == 0:
            print("⚠️  WARNING: No users found in database")
            print("   Run: python seed.py\n")
        else:
            print("✅ Database has users - ready to use!\n")
            
            # Show demo accounts
            admin = db.users.find_one({"email": "admin@urbanpulse.local"})
            if admin:
                print("🎯 Demo Accounts Available:")
                print("   Admin:  admin@urbanpulse.local / admin123")
                print("   Worker: worker@urbanpulse.local / worker123")
                print("   Citizen: citizen@urbanpulse.local / citizen123\n")
        
        print("="*70)
        print("✅ ALL CHECKS PASSED - You can run: python run.py")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}\n")
        print("="*70)
        print("🔧 QUICK FIX NEEDED")
        print("="*70 + "\n")
        print("MongoDB is not running or not configured.\n")
        print("Option 1: MongoDB Atlas (Recommended - FREE, 5 min)")
        print("  • Go to: https://www.mongodb.com/cloud/atlas/register")
        print("  • Create FREE account and cluster")
        print("  • Get connection string")
        print("  • Update MONGO_URI in .env file\n")
        print("Option 2: Local MongoDB")
        print("  • Download: https://www.mongodb.com/try/download/community")
        print("  • Install and start MongoDB service\n")
        print("📖 See QUICK_FIX.md for detailed step-by-step instructions")
        print("="*70 + "\n")
        
        return False

if __name__ == "__main__":
    test_connection()
