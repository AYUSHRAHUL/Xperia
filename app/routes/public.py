from datetime import datetime, timedelta
from bson import ObjectId
from flask import Blueprint, jsonify, request, g
import secrets

from .. import db
from ..middleware.auth import auth_required
from ..utils.email import send_email

public_bp = Blueprint("public", __name__)

@public_bp.get("/dashboard")
def public_dashboard():
    """Public dashboard statistics - no auth required"""
    
    # Total counts
    total_issues = db.issues.count_documents({})
    resolved_issues = db.issues.count_documents({"status": {"$in": ["RESOLVED", "CLOSED"]}})
    active_citizens = db.users.count_documents({"role": "citizen"})
    
    # Impact metrics
    impact = db.global_aggregates.find_one() or {}
    
    # Recent issues (last 10)
    recent = []
    for issue in db.issues.find().sort("createdAt", -1).limit(10):
        recent.append({
            "id": str(issue["_id"]),
            "title": issue["title"],
            "category": issue["category"],
            "status": issue["status"],
            "location": issue["location"],
            "createdAt": issue["createdAt"].isoformat()
        })
    
    # Category breakdown
    category_pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    categories = [{"category": c["_id"], "count": c["count"]} 
                  for c in db.issues.aggregate(category_pipeline)]
    
    # Status breakdown
    status_pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    statuses = [{"status": s["_id"], "count": s["count"]} 
                for s in db.issues.aggregate(status_pipeline)]
    
    # Top contributors
    top_pipeline = [
        {"$group": {"_id": "$reportedBy", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_data = list(db.issues.aggregate(top_pipeline))
    top_contributors = []
    for item in top_data:
        user = db.users.find_one({"_id": item["_id"]})
        if user:
            top_contributors.append({
                "name": user["name"],
                "points": user.get("points", 0),
                "issuesReported": item["count"]
            })
    
    return jsonify({
        "overview": {
            "totalIssues": total_issues,
            "resolvedIssues": resolved_issues,
            "activeCitizens": active_citizens,
            "resolutionRate": round((resolved_issues / total_issues * 100) if total_issues > 0 else 0, 2)
        },
        "impact": {
            "waterSaved": impact.get("totalWaterSaved", 0),
            "co2Reduced": impact.get("totalCo2Reduced", 0),
            "wasteRemoved": impact.get("totalWasteRemoved", 0),
            "issuesResolved": impact.get("totalIssuesResolved", 0)
        },
        "recentIssues": recent,
        "categoryBreakdown": categories,
        "statusBreakdown": statuses,
        "topContributors": top_contributors
    })

@public_bp.get("/map-data")
def public_map_data():
    """Get all issues for public map display"""
    
    status_filter = request.args.get("status")
    category_filter = request.args.get("category")
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    if category_filter:
        query["category"] = category_filter
    
    issues = []
    for issue in db.issues.find(query):
        issues.append({
            "id": str(issue["_id"]),
            "title": issue["title"],
            "category": issue["category"],
            "status": issue["status"],
            "location": issue["location"],
            "imageUrl": issue.get("imageUrl"),
            "createdAt": issue["createdAt"].isoformat()
        })
    
    return jsonify(issues)

@public_bp.post("/contact")
def contact_form():
    """Handle contact form submissions"""
    data = request.get_json() or {}
    
    required = ["name", "email", "subject", "message"]
    if not all(field in data for field in required):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Store contact submission
    db.contact_submissions.insert_one({
        "name": data["name"],
        "email": data["email"],
        "subject": data["subject"],
        "message": data["message"],
        "createdAt": datetime.utcnow(),
        "status": "pending"
    })
    
    # Send notification email to admin
    try:
        send_email(
            to="admin@urbanpulse.local",
            subject=f"New Contact Form: {data['subject']}",
            html=f"""
            <h2>New Contact Form Submission</h2>
            <p><strong>From:</strong> {data['name']} ({data['email']})</p>
            <p><strong>Subject:</strong> {data['subject']}</p>
            <p><strong>Message:</strong></p>
            <p>{data['message']}</p>
            """
        )
    except:
        pass  # Don't fail if email fails
    
    return jsonify({"message": "Thank you for contacting us! We'll respond soon."})

@public_bp.get("/statistics")
def public_statistics():
    """Detailed public statistics"""
    
    now = datetime.utcnow()
    
    # Time-based metrics
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    stats = {
        "today": {
            "reported": db.issues.count_documents({"createdAt": {"$gte": today_start}}),
            "resolved": db.issues.count_documents({
                "status": {"$in": ["RESOLVED", "CLOSED"]},
                "updatedAt": {"$gte": today_start}
            })
        },
        "thisWeek": {
            "reported": db.issues.count_documents({"createdAt": {"$gte": week_start}}),
            "resolved": db.issues.count_documents({
                "status": {"$in": ["RESOLVED", "CLOSED"]},
                "updatedAt": {"$gte": week_start}
            })
        },
        "thisMonth": {
            "reported": db.issues.count_documents({"createdAt": {"$gte": month_start}}),
            "resolved": db.issues.count_documents({
                "status": {"$in": ["RESOLVED", "CLOSED"]},
                "updatedAt": {"$gte": month_start}
            })
        }
    }
    
    return jsonify(stats)
