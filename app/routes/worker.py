from datetime import datetime

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
    items = []
    for doc in db.issues.find({"assignedTo": user["_id"]}).sort("createdAt", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        items.append(doc)
    return jsonify(items)


@worker_bp.put("/update-progress")
@auth_required(roles=["worker"])
def update_progress():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    status = data.get("status", "IN_PROGRESS")
    if not issue_id:
        return jsonify({"error": "issueId required"}), 400

    oid = ObjectId(issue_id)
    user = g.current_user
    res = db.issues.update_one(
        {"_id": oid, "assignedTo": user["_id"]},
        {"$set": {"status": status, "updatedAt": datetime.utcnow()}},
    )
    if res.matched_count == 0:
        return jsonify({"error": "Issue not found or not assigned"}), 400

    add_audit_log(oid, status, user["_id"])
    return jsonify({"status": status})


@worker_bp.put("/resolve")
@auth_required(roles=["worker"])
def resolve_issue():
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    completion_image = data.get("completionImageUrl")
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
    return jsonify({"status": "RESOLVED"})


