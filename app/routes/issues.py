from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required
from ..utils.impact_engine import calculate_impact, persist_impact
from ..utils.sdg_mapping import map_category_to_sdg


ISSUE_STATES = ["REPORTED", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]

issues_bp = Blueprint("issues", __name__)

# Import notifications (lazy import to avoid circular dependency if needed, but here it's fine)
from .notifications import create_notification


def add_audit_log(issue_id: ObjectId, action: str, user_id: ObjectId):
    db.audit_logs.insert_one(
        {
            "issueId": issue_id,
            "action": action,
            "performedBy": user_id,
            "timestamp": datetime.utcnow(),
        }
    )


def award_points(user_id: ObjectId, delta: int):
    if delta == 0:
        return
    db.users.update_one({"_id": user_id}, {"$inc": {"points": delta}})


@issues_bp.post("/create")
@auth_required(roles=["citizen"])
def create_issue():
    data = request.get_json() or {}
    required = ["title", "description", "category", "location"]
    if not all(field in data for field in required):
        return jsonify({"error": "Missing fields"}), 400

    mapping = map_category_to_sdg(data["category"])
    user = g.current_user
    now = datetime.utcnow()

    issue_doc = {
        "title": data["title"],
        "description": data["description"],
        "category": data["category"],
        "imageUrl": data.get("imageUrl"),
        "location": data["location"],
        "sdgTags": mapping["sdgTags"],
        "impactType": mapping["impactType"],
        "status": "REPORTED",
        "reportedBy": user["_id"],
        "assignedTo": None,
        "createdAt": now,
        "updatedAt": now,
    }
    res = db.issues.insert_one(issue_doc)
    issue_id = res.inserted_id

    # audit + gamification
    add_audit_log(issue_id, "REPORTED", user["_id"])
    points = 10
    if data.get("imageUrl"):
        points += 5
    award_points(user["_id"], points)

    # Notify all admins
    admins = db.users.find({"role": "admin"})
    for admin in admins:
        create_notification(
            admin["_id"], 
            "info", 
            "New Issue Reported", 
            f"New issue '{data['title']}' reported in {data['category']}"
        )

    return jsonify({"id": str(issue_id)}), 201


@issues_bp.get("/all")
@auth_required(roles=["admin"])
def get_all_issues():
    items = []
    for doc in db.issues.find().sort("createdAt", -1):
        doc["id"] = str(doc["_id"])
        doc["reportedBy"] = str(doc["reportedBy"])
        doc["assignedTo"] = str(doc["assignedTo"]) if doc.get("assignedTo") else None
        doc.pop("_id", None)
        items.append(doc)
    return jsonify(items)


@issues_bp.get("/public")
def get_public_issues():
    """Public map-friendly subset of issues without PII."""
    items = []
    for doc in db.issues.find({}, {"title": 1, "category": 1, "location": 1, "status": 1, "createdAt": 1, "imageUrl": 1, "description": 1}):
        items.append(
            {
                "id": str(doc["_id"]),
                "title": doc.get("title"),
                "category": doc.get("category"),
                "location": doc.get("location"),
                "status": doc.get("status"),
                "imageUrl": doc.get("imageUrl"),
                "description": doc.get("description"),
                "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
            }
        )
    return jsonify(items)


@issues_bp.get("/my")
@auth_required()
def get_my_issues():
    user = g.current_user
    items = []
    for doc in db.issues.find({"reportedBy": user["_id"]}).sort("createdAt", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        items.append(doc)
    return jsonify(items)


@issues_bp.get("/<issue_id>")
@auth_required()
def get_issue(issue_id):
    try:
        oid = ObjectId(issue_id)
    except Exception:
        return jsonify({"error": "Invalid id"}), 400

    doc = db.issues.find_one({"_id": oid})
    if not doc:
        return jsonify({"error": "Not found"}), 404

    timeline = []
    for log in db.audit_logs.find({"issueId": oid}).sort("timestamp", 1):
        timeline.append(
            {
                "action": log["action"],
                "performedBy": str(log["performedBy"]),
                "timestamp": log["timestamp"].isoformat(),
            }
        )

    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return jsonify({"issue": doc, "timeline": timeline})


@issues_bp.put("/verify")
@auth_required(roles=["admin"])
def verify_issue():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    if not issue_id:
        return jsonify({"error": "issueId required"}), 400

    oid = ObjectId(issue_id)
    issue = db.issues.find_one({"_id": oid})
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
        
    res = db.issues.update_one(
        {"_id": oid, "status": "REPORTED"}, {"$set": {"status": "VERIFIED", "updatedAt": datetime.utcnow()}}
    )
    if res.matched_count == 0:
        return jsonify({"error": "Issue not in REPORTED state"}), 400

    add_audit_log(oid, "VERIFIED", g.current_user["_id"])
    
    # Notify Citizen
    create_notification(issue["reportedBy"], "info", "Issue Verified", f"Your issue '{issue['title']}' has been verified by admin.")
    
    return jsonify({"status": "VERIFIED"})


@issues_bp.put("/assign")
@auth_required(roles=["admin"])
def assign_issue():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    worker_id = data.get("workerId")
    if not issue_id or not worker_id:
        return jsonify({"error": "Missing fields"}), 400

    oid = ObjectId(issue_id)
    wid = ObjectId(worker_id)

    worker = db.users.find_one({"_id": wid, "role": "worker"})
    if not worker:
        return jsonify({"error": "Worker not found"}), 400

    oid = ObjectId(issue_id)
    issue = db.issues.find_one({"_id": oid})
    if not issue:
        return jsonify({"error": "Issue not found"}), 404

    res = db.issues.update_one(
        {"_id": oid, "status": {"$in": ["VERIFIED", "REPORTED"]}},
        {
            "$set": {
                "assignedTo": wid,
                "status": "ASSIGNED",
                "updatedAt": datetime.utcnow(),
            }
        },
    )
    if res.matched_count == 0:
        return jsonify({"error": "Issue not assignable"}), 400

    add_audit_log(oid, "ASSIGNED", g.current_user["_id"])
    
    # Notify Worker
    create_notification(wid, "info", "New Task Assigned", f"You have been assigned to issue '{issue['title']}'")
    # Notify Citizen
    create_notification(issue["reportedBy"], "info", "Issue Assigned", f"A worker has been assigned to your issue '{issue['title']}'")
    
    return jsonify({"status": "ASSIGNED"})


@issues_bp.put("/update-status")
@auth_required()
def update_status():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    new_status = data.get("status")
    if not issue_id or new_status not in ISSUE_STATES:
        return jsonify({"error": "Invalid request"}), 400

    oid = ObjectId(issue_id)
    issue = db.issues.find_one({"_id": oid})
    if not issue:
        return jsonify({"error": "Issue not found"}), 404

    user = g.current_user
    role = user["role"]

    # Basic guard: only worker can move to IN_PROGRESS/RESOLVED, only admin can CLOSE
    if new_status in ["IN_PROGRESS", "RESOLVED"] and role != "worker":
        return jsonify({"error": "Only workers can update progress"}), 403
    if new_status == "CLOSED" and role != "admin":
        return jsonify({"error": "Only admin can close"}), 403

    db.issues.update_one({"_id": oid}, {"$set": {"status": new_status, "updatedAt": datetime.utcnow()}})
    add_audit_log(oid, new_status, user["_id"])

    # Notify Citizen
    create_notification(issue["reportedBy"], "info", f"Status: {new_status}", f"Your issue is now {new_status}")

    # Impact + points only when CLOSED
    if new_status == "CLOSED":
        impact = calculate_impact(issue, datetime.utcnow())
        persist_impact(oid, impact, issue.get("reportedBy"))
        # Award citizen points
        award_points(issue["reportedBy"], 20)
        create_notification(issue["reportedBy"], "success", "Points Earned!", "You earned 20 points for resolving an issue.")

    return jsonify({"status": new_status})


@issues_bp.put("/close")
@auth_required(roles=["admin"])
def close_issue():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    if not issue_id:
        return jsonify({"error": "issueId required"}), 400

    oid = ObjectId(issue_id)
    issue = db.issues.find_one({"_id": oid})
    if not issue:
        return jsonify({"error": "Not found"}), 404

    db.issues.update_one({"_id": oid}, {"$set": {"status": "CLOSED", "updatedAt": datetime.utcnow()}})
    add_audit_log(oid, "CLOSED", g.current_user["_id"])

    impact = calculate_impact(issue, datetime.utcnow())
    persist_impact(oid, impact, issue.get("reportedBy"))
    award_points(issue["reportedBy"], 20)
    
    # Notify Citizen
    create_notification(issue["reportedBy"], "success", "Issue Closed", "Your issue has been closed and points awarded!")

    return jsonify({"status": "CLOSED"})


