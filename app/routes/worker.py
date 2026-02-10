from datetime import datetime, timedelta

from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required
from .issues import add_audit_log


worker_bp = Blueprint("worker", __name__)


@worker_bp.get("/tasks")
@auth_required(roles=["worker"])
def get_tasks():
    user = g.current_user
    status_filter = request.args.get("status")

    query = {"assignedTo": user["_id"]}
    if status_filter:
        if status_filter == "active":
             query["status"] = {"$in": ["ASSIGNED", "IN_PROGRESS"]}
        elif status_filter == "completed":
             query["status"] = {"$in": ["RESOLVED", "CLOSED"]}
        else:
             query["status"] = status_filter

    items = []
    for doc in db.issues.find(query).sort("updatedAt", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        doc["createdAt"] = doc["createdAt"].isoformat() if doc.get("createdAt") else None
        doc["updatedAt"] = doc["updatedAt"].isoformat() if doc.get("updatedAt") else None
        items.append(doc)
    return jsonify(items)


@worker_bp.get("/stats")
@auth_required(roles=["worker"])
def get_worker_stats():
    user = g.current_user
    
    total_assigned = db.issues.count_documents({"assignedTo": user["_id"]})
    resolved = db.issues.count_documents({"assignedTo": user["_id"], "status": {"$in": ["RESOLVED", "CLOSED"]}})
    pending = db.issues.count_documents({"assignedTo": user["_id"], "status": {"$in": ["ASSIGNED", "IN_PROGRESS"]}})
    
    # Calculate average resolution time (simple approximation)
    avg_resolution_pipeline = [
        {"$match": {"assignedTo": user["_id"], "status": {"$in": ["RESOLVED", "CLOSED"]}}},
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
    avg_hours = (avg_result[0]["avgTime"] / (1000 * 60 * 60)) if avg_result else 0

    return jsonify({
        "totalAssigned": total_assigned,
        "resolved": resolved,
        "pending": pending,
        "avgResolutionHours": round(avg_hours, 1)
    })


@worker_bp.put("/update-progress")
@auth_required(roles=["worker"])
def update_progress():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    status = data.get("status", "IN_PROGRESS")
    note = data.get("note")
    
    if not issue_id:
        return jsonify({"error": "issueId required"}), 400

    oid = ObjectId(issue_id)
    user = g.current_user
    
    update_data = {"status": status, "updatedAt": datetime.utcnow()}
    
    res = db.issues.update_one(
        {"_id": oid, "assignedTo": user["_id"]},
        {"$set": update_data},
    )
    
    if res.matched_count == 0:
        return jsonify({"error": "Issue not found or not assigned"}), 400

    add_audit_log(oid, status, user["_id"])
    
    # Add note if provided
    if note:
        db.work_notes.insert_one({
            "issueId": oid,
            "workerId": user["_id"],
            "note": note,
            "createdAt": datetime.utcnow()
        })
        
    return jsonify({"status": status})


@worker_bp.put("/resolve")
@auth_required(roles=["worker"])
def resolve_issue():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    completion_image = data.get("completionImageUrl")
    note = data.get("note")

    if not issue_id:
        return jsonify({"error": "issueId required"}), 400

    oid = ObjectId(issue_id)
    user = g.current_user
    update = {
        "status": "RESOLVED",
        "updatedAt": datetime.utcnow(),
    }
    if completion_image:
        update["completionImageUrl"] = completion_image

    res = db.issues.update_one({"_id": oid, "assignedTo": user["_id"]}, {"$set": update})
    if res.matched_count == 0:
        return jsonify({"error": "Issue not found or not assigned"}), 400

    add_audit_log(oid, "RESOLVED", user["_id"])
    
    if note:
        db.work_notes.insert_one({
            "issueId": oid,
            "workerId": user["_id"],
            "note": note,
            "createdAt": datetime.utcnow()
        })

    # Notify Citizen (if imported to avoid circular dependency, do it here or assume issues.py handles notifications on status change?)
    # Ideally, notifications logic should be centralized or triggered via events.
    # For now, let's keep it simple as notification triggers are mainly in issues.py status updates.

    return jsonify({"status": "RESOLVED"})
