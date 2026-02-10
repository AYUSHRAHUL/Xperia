from datetime import datetime
from bson import ObjectId
from flask import Blueprint, jsonify, request, g
from .. import db
from ..middleware.auth import auth_required

notifications_bp = Blueprint("notifications", __name__)

def create_notification(user_id: ObjectId, type: str, title: str, message: str, link: str = None):
    """
    Creates a new notification for a user.
    Types: 'info', 'success', 'warning', 'error'
    """
    db.notifications.insert_one({
        "userId": user_id,
        "type": type,
        "title": title,
        "message": message,
        "link": link,
        "read": False,
        "createdAt": datetime.utcnow()
    })

@notifications_bp.get("/")
@auth_required()
def get_notifications():
    user = g.current_user
    limit = int(request.args.get("limit", 20))
    
    notifications = []
    cursor = db.notifications.find({"userId": user["_id"]}).sort("createdAt", -1).limit(limit)
    
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["userId"] = str(doc["userId"])
        doc.pop("_id", None)
        doc["createdAt"] = doc["createdAt"].isoformat()
        notifications.append(doc)
        
    # Get unread count
    unread_count = db.notifications.count_documents({"userId": user["_id"], "read": False})
    
    return jsonify({
        "notifications": notifications,
        "unreadCount": unread_count
    })

@notifications_bp.put("/<notification_id>/read")
@auth_required()
def mark_read(notification_id):
    try:
        oid = ObjectId(notification_id)
    except:
        return jsonify({"error": "Invalid ID"}), 400
        
    user = g.current_user
    res = db.notifications.update_one(
        {"_id": oid, "userId": user["_id"]},
        {"$set": {"read": True}}
    )
    
    if res.matched_count == 0:
        return jsonify({"error": "Notification not found"}), 404
        
    return jsonify({"status": "marked read"})

@notifications_bp.put("/read-all")
@auth_required()
def mark_all_read():
    user = g.current_user
    db.notifications.update_many(
        {"userId": user["_id"], "read": False},
        {"$set": {"read": True}}
    )
    return jsonify({"status": "all marked read"})
