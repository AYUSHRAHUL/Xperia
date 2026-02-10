from datetime import datetime
from math import sqrt

from bson import ObjectId
from flask import Blueprint, jsonify, request

from .. import db
from ..middleware.auth import auth_required


admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/all-issues")
@auth_required(roles=["admin"])
def all_issues():
    """Get all issues for admin dashboard."""
    issues = []
    for doc in db.issues.find({}).sort("createdAt", -1):
        issues.append({
            "_id": str(doc["_id"]),
            "title": doc.get("title"),
            "category": doc.get("category"),
            "description": doc.get("description"),
            "imageUrl": doc.get("imageUrl"),
            "status": doc.get("status"),
            "location": doc.get("location"),
            "assignedTo": str(doc.get("assignedTo")) if doc.get("assignedTo") else None,
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
            "updatedAt": doc.get("updatedAt").isoformat() if doc.get("updatedAt") else None,
        })
    return jsonify(issues)


@admin_bp.get("/users")
@auth_required(roles=["admin"])
def get_users():
    """Get all users."""
    users = []
    for u in db.users.find({}, {"password": 0}):
        users.append({
            "id": str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "role": u.get("role"),
            "points": u.get("points", 0),
            "createdAt": u.get("createdAt").isoformat() if u.get("createdAt") else None,
        })
    return jsonify(users)


@admin_bp.post("/assign-issue")
@auth_required(roles=["admin"])
def assign_issue():
    """Assign an issue to a worker."""
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    worker_id = data.get("workerId")
    
    if not issue_id or not worker_id:
        return jsonify({"error": "Missing issueId or workerId"}), 400
    
    try:
        result = db.issues.update_one(
            {"_id": ObjectId(issue_id)},
            {
                "$set": {
                    "assignedTo": ObjectId(worker_id),
                    "status": "ASSIGNED",
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Issue not found"}), 404
        
        return jsonify({"message": "Issue assigned successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.get("/user-stats")
@auth_required(roles=["admin"])
def user_stats():
    """Get user statistics."""
    total_users = db.users.count_documents({})
    citizens = db.users.count_documents({"role": "citizen"})
    workers = db.users.count_documents({"role": "worker"})
    admins = db.users.count_documents({"role": "admin"})
    
    return jsonify({
        "total": total_users,
        "citizens": citizens,
        "workers": workers,
        "admins": admins
    })


@admin_bp.get("/department-performance")
@auth_required(roles=["admin"])
def department_performance():
    # Simplified: treat category as department
    pipeline = [
        {
            "$group": {
                "_id": "$category",
                "total": {"$sum": 1},
                "closed": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "CLOSED"]}, 1, 0],
                    }
                },
                "avgResolutionHours": {
                    "$avg": {
                        "$divide": [{"$subtract": ["$updatedAt", "$createdAt"]}, 1000 * 60 * 60],
                    }
                },
            }
        }
    ]
    rows = list(db.issues.aggregate(pipeline))
    result = []
    for r in rows:
        closure_rate = (r.get("closed", 0) / r.get("total", 1)) if r.get("total") else 0
        avg_res = r.get("avgResolutionHours") or 1
        rating = closure_rate / avg_res if avg_res > 0 else 0
        result.append(
            {
                "department": r["_id"],
                "totalIssues": r.get("total", 0),
                "closedIssues": r.get("closed", 0),
                "avgResolutionHours": avg_res,
                "rating": rating,
            }
        )
    return jsonify(result)


@admin_bp.get("/workers")
@auth_required(roles=["admin"])
def list_workers():
    """List workers for assignment UI."""
    workers = []
    for u in db.users.find({"role": "worker"}, {"name": 1}):
        workers.append({"id": str(u["_id"]), "name": u.get("name")})
    return jsonify(workers)


@admin_bp.get("/recurring-issues")
@auth_required(roles=["admin"])
def recurring_issues():
    # naive structural problem detection: same lat/lng rounded to 3 decimals and count > 3
    issues = list(db.issues.find({}))
    buckets = {}
    for i in issues:
        loc = i.get("location") or {}
        lat = loc.get("lat")
        lng = loc.get("lng")
        if lat is None or lng is None:
            continue
        key = (round(float(lat), 3), round(float(lng), 3))
        buckets.setdefault(key, []).append(i)

    structural = []
    for (lat, lng), group in buckets.items():
        if len(group) > 3:
            structural.append(
                {
                    "lat": lat,
                    "lng": lng,
                    "count": len(group),
                    "issueIds": [str(g["_id"]) for g in group],
                    "label": "STRUCTURAL PROBLEM",
                }
            )
    return jsonify(structural)


@admin_bp.get("/resolution-time")
@auth_required(roles=["admin"])
def resolution_time():
    pipeline = [
        {"$match": {"status": "CLOSED"}},
        {
            "$project": {
                "category": 1,
                "resolutionHours": {
                    "$divide": [{"$subtract": ["$updatedAt", "$createdAt"]}, 1000 * 60 * 60],
                },
            }
        },
        {
            "$group": {
                "_id": "$category",
                "avgResolutionHours": {"$avg": "$resolutionHours"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = list(db.issues.aggregate(pipeline))
    result = [
        {
            "category": r["_id"],
            "avgResolutionHours": r.get("avgResolutionHours", 0),
        }
        for r in rows
    ]
    return jsonify(result)


