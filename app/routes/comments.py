from datetime import datetime
from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required

comments_bp = Blueprint("comments", __name__)

@comments_bp.post("/")
@auth_required()
def add_comment():
    """Add a comment to an issue"""
    data = request.get_json() or {}
    issue_id = data.get("issueId")
    comment_text = data.get("comment")
    
    if not issue_id or not comment_text:
        return jsonify({"error": "Missing fields"}), 400
    
    try:
        oid = ObjectId(issue_id)
    except:
        return jsonify({"error": "Invalid issue ID"}), 400
    
    # Verify issue exists
    issue = db.issues.find_one({"_id": oid})
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    
    user = g.current_user
    comment_doc = {
        "issueId": oid,
        "userId": user["_id"],
        "userName": user["name"],
        "userRole": user["role"],
        "comment": comment_text.strip(),
        "createdAt": datetime.utcnow()
    }
    
    result = db.comments.insert_one(comment_doc)
    
    # Notify issue reporter if commenter is different
    if user["_id"] != issue["reportedBy"]:
        from .notifications import create_notification
        create_notification(
            issue["reportedBy"],
            "info",
            "New Comment",
            f"{user['name']} commented on your issue"
        )
    
    return jsonify({
        "id": str(result.inserted_id),
        "message": "Comment added successfully"
    }), 201

@comments_bp.get("/<issue_id>")
def get_comments(issue_id):
    """Get all comments for an issue"""
    try:
        oid = ObjectId(issue_id)
    except:
        return jsonify({"error": "Invalid issue ID"}), 400
    
    comments = []
    cursor = db.comments.find({"issueId": oid}).sort("createdAt", 1)
    
    for doc in cursor:
        comments.append({
            "id": str(doc["_id"]),
            "userName": doc["userName"],
            "userRole": doc["userRole"],
            "comment": doc["comment"],
            "createdAt": doc["createdAt"].isoformat()
        })
    
    return jsonify(comments)

@comments_bp.delete("/<comment_id>")
@auth_required()
def delete_comment(comment_id):
    """Delete a comment (only by author or admin)"""
    try:
        oid = ObjectId(comment_id)
    except:
        return jsonify({"error": "Invalid comment ID"}), 400
    
    user = g.current_user
    comment = db.comments.find_one({"_id": oid})
    
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    
    # Only author or admin can delete
    if comment["userId"] != user["_id"] and user["role"] != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    db.comments.delete_one({"_id": oid})
    return jsonify({"message": "Comment deleted"})
