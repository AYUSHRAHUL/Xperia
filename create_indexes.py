"""
Database index creation script for performance optimization
Run this after initial setup to create indexes on frequently queried fields
"""

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT, GEO2D
import os
from dotenv import load_dotenv

def create_indexes():
    load_dotenv()
    
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "urban_pulse")
    
    print(f"Connecting to MongoDB...")
    client = MongoClient(mongo_uri)
    db = client[db_name]
    
    print("Creating indexes...")
    
    # Users collection
    print("  - users indexes")
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.users.create_index([("role", ASCENDING)])
    db.users.create_index([("points", DESCENDING)])
    db.users.create_index([("createdAt", DESCENDING)])
    
    # Issues collection
    print("  - issues indexes")
    db.issues.create_index([("status", ASCENDING)])
    db.issues.create_index([("category", ASCENDING)])
    db.issues.create_index([("reportedBy", ASCENDING)])
    db.issues.create_index([("assignedTo", ASCENDING)])
    db.issues.create_index([("createdAt", DESCENDING)])
    db.issues.create_index([("updatedAt", DESCENDING)])
    
    # Geospatial index for location-based queries
    db.issues.create_index([
        ("location.lat", ASCENDING),
        ("location.lng", ASCENDING)
    ])
    
    # Text search index
    db.issues.create_index([
        ("title", TEXT),
        ("description", TEXT),
        ("category", TEXT)
    ])
    
    # Compound indexes for common queries
    db.issues.create_index([("status", ASCENDING), ("createdAt", DESCENDING)])
    db.issues.create_index([("category", ASCENDING), ("status", ASCENDING)])
    
    # Notifications collection
    print("  - notifications indexes")
    db.notifications.create_index([("userId", ASCENDING), ("createdAt", DESCENDING)])
    db.notifications.create_index([("userId", ASCENDING), ("read", ASCENDING)])
    db.notifications.create_index([("createdAt", DESCENDING)])
    
    # Comments collection
    print("  - comments indexes")
    db.comments.create_index([("issueId", ASCENDING), ("createdAt", ASCENDING)])
    db.comments.create_index([("userId", ASCENDING)])
    
    # Votes collection
    print("  - votes indexes")
    db.votes.create_index([("issueId", ASCENDING)])
    db.votes.create_index([("userId", ASCENDING), ("issueId", ASCENDING)], unique=True)
    
    # Audit logs collection
    print("  - audit_logs indexes")
    db.audit_logs.create_index([("issueId", ASCENDING), ("timestamp", ASCENDING)])
    db.audit_logs.create_index([("performedBy", ASCENDING)])
    db.audit_logs.create_index([("timestamp", DESCENDING)])
    
    # Impact metrics collection
    print("  - impact_metrics indexes")
    db.impact_metrics.create_index([("issueId", ASCENDING)])
    db.impact_metrics.create_index([("createdAt", DESCENDING)])
    
    print("\n✅ All indexes created successfully!")
    print("\nIndexes created:")
    print(f"  - Users: {len(db.users.index_information())} indexes")
    print(f"  - Issues: {len(db.issues.index_information())} indexes")
    print(f"  - Notifications: {len(db.notifications.index_information())} indexes")
    print(f"  - Comments: {len(db.comments.index_information())} indexes")
    print(f"  - Votes: {len(db.votes.index_information())} indexes")
    print(f"  - Audit Logs: {len(db.audit_logs.index_information())} indexes")
    print(f"  - Impact Metrics: {len(db.impact_metrics.index_information())} indexes")

if __name__ == "__main__":
    create_indexes()
