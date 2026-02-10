import csv
import io
from datetime import datetime, timedelta
from bson import ObjectId
from flask import Blueprint, jsonify, request, Response, g

from .. import db
from ..middleware.auth import auth_required

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.get("/dashboard-stats")
@auth_required(roles=["admin"])
def get_dashboard_stats():
    """Comprehensive dashboard statistics"""
    
    # Time ranges
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    # Total counts
    total_issues = db.issues.count_documents({})
    total_users = db.users.count_documents({})
    total_citizens = db.users.count_documents({"role": "citizen"})
    total_workers = db.users.count_documents({"role": "worker"})
    
    # Status breakdown
    status_counts = {}
    for status in ["REPORTED", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
        status_counts[status] = db.issues.count_documents({"status": status})
    
    # Category breakdown
    category_pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    categories = list(db.issues.aggregate(category_pipeline))
    
    # Time-based metrics
    today_issues = db.issues.count_documents({"createdAt": {"$gte": today_start}})
    week_issues = db.issues.count_documents({"createdAt": {"$gte": week_start}})
    month_issues = db.issues.count_documents({"createdAt": {"$gte": month_start}})
    
    # Resolution metrics
    resolved_count = db.issues.count_documents({"status": {"$in": ["RESOLVED", "CLOSED"]}})
    resolution_rate = (resolved_count / total_issues * 100) if total_issues > 0 else 0
    
    # Average resolution time
    avg_resolution_pipeline = [
        {"$match": {"status": {"$in": ["RESOLVED", "CLOSED"]}}},
        {
            "$project": {
                "resolutionTime": {
                    "$subtract": ["$updatedAt", "$createdAt"]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "avgTime": {"$avg": "$resolutionTime"}
            }
        }
    ]
    avg_result = list(db.issues.aggregate(avg_resolution_pipeline))
    avg_resolution_hours = (avg_result[0]["avgTime"] / (1000 * 60 * 60)) if avg_result else 0
    
    # Top contributors
    top_reporters_pipeline = [
        {"$group": {"_id": "$reportedBy", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_reporters_data = list(db.issues.aggregate(top_reporters_pipeline))
    top_reporters = []
    for item in top_reporters_data:
        user = db.users.find_one({"_id": item["_id"]})
        if user:
            top_reporters.append({
                "name": user["name"],
                "count": item["count"]
            })
    
    # Impact metrics
    impact_totals = db.global_aggregates.find_one() or {}
    
    return jsonify({
        "overview": {
            "totalIssues": total_issues,
            "totalUsers": total_users,
            "totalCitizens": total_citizens,
            "totalWorkers": total_workers,
            "resolutionRate": round(resolution_rate, 2),
            "avgResolutionHours": round(avg_resolution_hours, 2)
        },
        "timeMetrics": {
            "today": today_issues,
            "thisWeek": week_issues,
            "thisMonth": month_issues
        },
        "statusBreakdown": status_counts,
        "categoryBreakdown": [{"category": c["_id"], "count": c["count"]} for c in categories],
        "topReporters": top_reporters,
        "impact": {
            "waterSaved": impact_totals.get("totalWaterSaved", 0),
            "co2Reduced": impact_totals.get("totalCo2Reduced", 0),
            "wasteRemoved": impact_totals.get("totalWasteRemoved", 0)
        }
    })

@analytics_bp.get("/trends")
def get_trends():
    """Get issue trends over time"""
    days = int(request.args.get("days", 30))
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    pipeline = [
        {"$match": {"createdAt": {"$gte": start_date}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$createdAt"
                    }
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    trends = list(db.issues.aggregate(pipeline))
    
    return jsonify([{"date": t["_id"], "count": t["count"]} for t in trends])

@analytics_bp.get("/export/issues")
@auth_required(roles=["admin"])
def export_issues_csv():
    """Export issues to CSV"""
    
    # Query parameters
    status = request.args.get("status")
    category = request.args.get("category")
    
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Title", "Category", "Status", "Reporter Email",
        "Created At", "Updated At", "Location"
    ])
    
    # Write data
    for issue in db.issues.find(query).sort("createdAt", -1):
        reporter = db.users.find_one({"_id": issue["reportedBy"]})
        reporter_email = reporter["email"] if reporter else "Unknown"
        
        writer.writerow([
            str(issue["_id"]),
            issue["title"],
            issue["category"],
            issue["status"],
            reporter_email,
            issue["createdAt"].strftime("%Y-%m-%d %H:%M:%S"),
            issue["updatedAt"].strftime("%Y-%m-%d %H:%M:%S"),
            issue["location"].get("address", "")
        ])
    
    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=issues_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@analytics_bp.get("/hotspots")
@auth_required(roles=["admin"])
def get_hotspots():
    """Identify recurring issue hotspots"""
    
    # Group by location (approximate)
    pipeline = [
        {
            "$group": {
                "_id": {
                    "lat": {"$round": [{"$multiply": ["$location.lat", 100]}, 0]},
                    "lng": {"$round": [{"$multiply": ["$location.lng", 100]}, 0]}
                },
                "count": {"$sum": 1},
                "issues": {"$push": {"title": "$title", "category": "$category"}}
            }
        },
        {"$match": {"count": {"$gte": 2}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    hotspots = list(db.issues.aggregate(pipeline))
    
    result = []
    for spot in hotspots:
        result.append({
            "location": {
                "lat": spot["_id"]["lat"] / 100,
                "lng": spot["_id"]["lng"] / 100
            },
            "issueCount": spot["count"],
            "recentIssues": spot["issues"][:3]
        })
    
    return jsonify(result)
