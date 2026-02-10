from datetime import datetime
from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required

users_bp = Blueprint("users", __name__)

@users_bp.get("/")
@auth_required(roles=["admin"])
def get_all_users():
    """Get all users with filtering"""
    role_filter = request.args.get("role")
    search = request.args.get("search", "").strip()
    
    query = {}
    if role_filter:
        query["role"] = role_filter
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    users = []
    for user in db.users.find(query).sort("createdAt", -1):
        users.append({
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "points": user.get("points", 0),
            "createdAt": user["createdAt"].isoformat()
        })
    
    return jsonify(users)

@users_bp.get("/<user_id>")
@auth_required(roles=["admin"])
def get_user(user_id):
    """Get user details"""
    try:
        oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid user ID"}), 400
    
    user = db.users.find_one({"_id": oid})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get user statistics
    issues_reported = db.issues.count_documents({"reportedBy": oid})
    issues_resolved = db.issues.count_documents({"assignedTo": oid, "status": {"$in": ["RESOLVED", "CLOSED"]}})
    
    return jsonify({
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "points": user.get("points", 0),
        "createdAt": user["createdAt"].isoformat(),
        "stats": {
            "issuesReported": issues_reported,
            "issuesResolved": issues_resolved
        }
    })

@users_bp.put("/<user_id>")
@auth_required(roles=["admin"])
def update_user(user_id):
    """Update user details (admin only)"""
    try:
        oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid user ID"}), 400
    
    data = request.get_json() or {}
    
    update_fields = {}
    if "name" in data:
        update_fields["name"] = data["name"].strip()
    if "role" in data and data["role"] in ["citizen", "worker", "admin"]:
        update_fields["role"] = data["role"]
    if "points" in data and isinstance(data["points"], int):
        update_fields["points"] = data["points"]
    
    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400
    
    result = db.users.update_one(
        {"_id": oid},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"message": "User updated successfully"})

@users_bp.delete("/<user_id>")
@auth_required(roles=["admin"])
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
        oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid user ID"}), 400
    
    # Prevent deleting yourself
    if oid == g.current_user["_id"]:
        return jsonify({"error": "Cannot delete your own account"}), 400
    
    # Check if user exists
    user = db.users.find_one({"_id": oid})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Delete user
    db.users.delete_one({"_id": oid})
    
    # Clean up related data
    db.notifications.delete_many({"userId": oid})
    db.comments.delete_many({"userId": oid})
    db.votes.delete_many({"userId": oid})
    
    return jsonify({"message": "User deleted successfully"})

@users_bp.get("/workers/available")
@auth_required(roles=["admin"])
def get_available_workers():
    """Get list of workers for assignment"""
    workers = []
    for worker in db.users.find({"role": "worker"}):
        # Count assigned tasks
        assigned_count = db.issues.count_documents({
            "assignedTo": worker["_id"],
            "status": {"$in": ["ASSIGNED", "IN_PROGRESS"]}
        })
        
        workers.append({
            "id": str(worker["_id"]),
            "name": worker["name"],
            "email": worker["email"],
            "assignedTasks": assigned_count
        })
    
    # Sort by least assigned
    workers.sort(key=lambda x: x["assignedTasks"])
    
    return jsonify(workers)
