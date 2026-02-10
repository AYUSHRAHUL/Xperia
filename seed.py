from datetime import datetime, timedelta
import os
import random

from pymongo import MongoClient
from dotenv import load_dotenv

from app.utils.security import hash_password

# Constants
CATEGORIES = ["Water Leakage", "Garbage Dump", "Pothole", "Broken Streetlight", "Traffic Signal"]

def seed():
    # Load environment variables
    load_dotenv()
    
    # Get MongoDB URI from environment
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "urban_pulse")
    
    print(f"Connecting to MongoDB at {mongo_uri}...")
    client = MongoClient(mongo_uri)
    db = client[db_name]
    
    print(f"Clearing existing data...")
    db.users.delete_many({})
    db.issues.delete_many({})
    db.impact_metrics.delete_many({})
    db.audit_logs.delete_many({})
    db.global_aggregates.delete_many({})
    db.notifications.delete_many({})

    print("Creating users...")
    # Admin
    admin_id = db.users.insert_one({
        "name": "Admin User",
        "email": "admin@urbanpulse.local",
        "password": hash_password("admin123"),
        "role": "admin",
        "points": 0,
        "createdAt": datetime.utcnow(),
    }).inserted_id

    # Workers
    worker1_id = db.users.insert_one({
        "name": "Field Worker 1",
        "email": "worker1@urbanpulse.local",
        "password": hash_password("worker123"),
        "role": "worker",
        "points": 0,
        "createdAt": datetime.utcnow(),
    }).inserted_id

    worker2_id = db.users.insert_one({
        "name": "Field Worker 2",
        "email": "worker2@urbanpulse.local",
        "password": hash_password("worker123"),
        "role": "worker",
        "points": 0,
        "createdAt": datetime.utcnow(),
    }).inserted_id

    # Citizens
    citizen_id = db.users.insert_one({
        "name": "Rahul Citizen",
        "email": "citizen@urbanpulse.local",
        "password": hash_password("citizen123"),
        "role": "citizen",
        "points": 120, # Initial points
        "createdAt": datetime.utcnow(),
    }).inserted_id

    other_citizens = []
    for i in range(5):
        uid = db.users.insert_one({
            "name": f"Citizen {i+1}",
            "email": f"citizen{i+1}@urbanpulse.local",
            "password": hash_password("password"),
            "role": "citizen",
            "points": random.randint(10, 300),
            "createdAt": datetime.utcnow(),
        }).inserted_id
        other_citizens.append(uid)

    print("Creating issues...")
    issues_data = [
        {"title": "Pothole on Main Road", "cat": "Pothole", "status": "REPORTED", "desc": "Large pothole causing traffic slowdown near the junction." },
        {"title": "Overflowing Garbage Bin", "cat": "Garbage Dump", "status": "VERIFIED", "desc": "Bin hasn't been cleared for 3 days. Bad smell." },
        {"title": "Streetlight not working", "cat": "Broken Streetlight", "status": "ASSIGNED", "desc": "Corner streetlight is flickering and off." },
        {"title": "Water Pipe Burst", "cat": "Water Leakage", "status": "IN_PROGRESS", "desc": "Severe leakage wasting clean water." },
        {"title": "Traffic Light Stuck", "cat": "Traffic Signal", "status": "RESOLVED", "desc": "Red light stuck for 10 mins." },
        {"title": "Illegal Dumping", "cat": "Garbage Dump", "status": "CLOSED", "desc": "Construction waste dumped on sidewalk." },
        {"title": "Another Pothole", "cat": "Pothole", "status": "REPORTED", "desc": "Small but dangerous pothole for bikers." },
        {"title": "Park Light Broken", "cat": "Broken Streetlight", "status": "VERIFIED", "desc": "Path lights inside the park are broken." },
        {"title": "Sewage Leak", "cat": "Water Leakage", "status": "ASSIGNED", "desc": "Sewage water leaking onto the street." },
        {"title": "Signal Malfunction", "cat": "Traffic Signal", "status": "CLOSED", "desc": "All lights off at 4th block crossing." },
    ]

    base_lat, base_lng = 12.9716, 77.5946
    
    created_issues = []

    for idx, item in enumerate(issues_data):
        # Random location drift
        lat = base_lat + (random.random() - 0.5) * 0.05
        lng = base_lng + (random.random() - 0.5) * 0.05
        
        reporter = citizen_id if idx % 2 == 0 else random.choice(other_citizens)
        worker = worker1_id if idx % 2 == 0 else worker2_id
        
        assigned_to = None
        if item["status"] in ["ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
            assigned_to = worker

        issue_doc = {
            "title": item["title"],
            "description": item["desc"],
            "category": item["cat"],
            "imageUrl": f"https://picsum.photos/seed/{idx}/400/300" if idx % 3 == 0 else None,
            "location": {"lat": lat, "lng": lng, "address": f"Location {idx}, Bangalore"},
            "sdgTags": [11, 6] if "Water" in item["cat"] else [11],
            "impactType": "water" if "Water" in item["cat"] else "waste" if "Garbage" in item["cat"] else "safety",
            "status": item["status"],
            "reportedBy": reporter,
            "assignedTo": assigned_to,
            "createdAt": datetime.utcnow() - timedelta(days=random.randint(0, 5)),
            "updatedAt": datetime.utcnow(),
        }
        
        res = db.issues.insert_one(issue_doc)
        iid = res.inserted_id
        created_issues.append(iid)

        # Create notifications for reporter
        if reporter == citizen_id:
            db.notifications.insert_one({
                "userId": citizen_id,
                "type": "info",
                "title": f"Issue Update: {item['title']}",
                "message": f"Status is now {item['status']}",
                "read": False,
                "createdAt": datetime.utcnow() - timedelta(minutes=random.randint(10, 100))
            })

        # Create notifications for worker if assigned
        if assigned_to:
             db.notifications.insert_one({
                "userId": assigned_to,
                "type": "info",
                "title": "New Task Assigned",
                "message": f"You have been assigned: {item['title']}",
                "read": False,
                "createdAt": datetime.utcnow() - timedelta(minutes=random.randint(10, 100))
            })

        # Add Impact Data if resolved/closed
        if item["status"] in ["RESOLVED", "CLOSED"]:
             db.impact_metrics.insert_one({
                "issueId": iid,
                "waterSaved": random.randint(100, 500) if "Water" in item["cat"] else 0,
                "co2Reduced": random.randint(10, 50) if "Garbage" in item["cat"] else 0,
                "wasteRemoved": random.randint(50, 200) if "Garbage" in item["cat"] else 0,
                "fuelSaved": 0,
                "safetyScore": 10,
                "createdAt": datetime.utcnow()
             })

    print("Aggregating global stats...")
    db.global_aggregates.insert_one({
        "totalWaterSaved": 12500,
        "totalCo2Reduced": 8750,
        "totalWasteRemoved": 15200,
        "totalFuelSaved": 0,
        "totalIssuesResolved": 45,
        "citizenParticipationCount": 1234,
        "updatedAt": datetime.utcnow()
    })

    print("Seed complete! Users created:")
    print("Admin: admin@urbanpulse.local / admin123")
    print("Worker: worker1@urbanpulse.local / worker123")
    print("Citizen: citizen@urbanpulse.local / citizen123")

if __name__ == "__main__":
    seed()
