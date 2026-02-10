from flask import Blueprint, jsonify, request
from .. import db

search_bp = Blueprint("search", __name__)

@search_bp.get("/")
def search_issues():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    # Regex search for simplicity (Case insensitive)
    regex = {"$regex": query, "$options": "i"}
    
    # Search in title, description, category, or location.address
    criteria = {
        "$or": [
            {"title": regex},
            {"description": regex},
            {"category": regex},
            {"location.address": regex}
        ]
    }
    
    # Only return public fields for safety, unless auth is added
    # For now, let's return safe public data + status
    issues = []
    cursor = db.issues.find(criteria).limit(20)
    
    for doc in cursor:
        issues.append({
            "id": str(doc["_id"]),
            "title": doc.get("title"),
            "description": doc.get("description"), # Optional: truncate
            "category": doc.get("category"),
            "status": doc.get("status"),
            "imageUrl": doc.get("imageUrl"),
            "location": doc.get("location"),
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None
        })
        
    return jsonify(issues)
