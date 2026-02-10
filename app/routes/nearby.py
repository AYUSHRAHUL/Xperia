from datetime import datetime
from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required

nearby_bp = Blueprint("nearby", __name__)

@nearby_bp.get("/issues")
def get_nearby_issues():
    """Get issues near a location (public endpoint)"""
    
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
        radius_km = float(request.args.get("radius", 5))  # Default 5km
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400
    
    # Convert km to degrees (approximate)
    # 1 degree ≈ 111 km
    radius_deg = radius_km / 111.0
    
    # Find issues within bounding box
    query = {
        "location.lat": {"$gte": lat - radius_deg, "$lte": lat + radius_deg},
        "location.lng": {"$gte": lng - radius_deg, "$lte": lng + radius_deg}
    }
    
    # Optional filters
    status = request.args.get("status")
    category = request.args.get("category")
    
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    
    issues = []
    for issue in db.issues.find(query).limit(50):
        # Calculate approximate distance
        lat_diff = abs(issue["location"]["lat"] - lat)
        lng_diff = abs(issue["location"]["lng"] - lng)
        distance = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111  # Approximate km
        
        issues.append({
            "id": str(issue["_id"]),
            "title": issue["title"],
            "category": issue["category"],
            "status": issue["status"],
            "location": issue["location"],
            "distance": round(distance, 2),
            "imageUrl": issue.get("imageUrl"),
            "createdAt": issue["createdAt"].isoformat()
        })
    
    # Sort by distance
    issues.sort(key=lambda x: x["distance"])
    
    return jsonify({
        "center": {"lat": lat, "lng": lng},
        "radius": radius_km,
        "count": len(issues),
        "issues": issues
    })

@nearby_bp.get("/hotspots")
def get_hotspots():
    """Identify areas with multiple issues"""
    
    # Group issues by approximate location (0.01 degree grid ≈ 1km)
    pipeline = [
        {
            "$group": {
                "_id": {
                    "lat": {"$round": [{"$multiply": ["$location.lat", 100]}, 0]},
                    "lng": {"$round": [{"$multiply": ["$location.lng", 100]}, 0]}
                },
                "count": {"$sum": 1},
                "categories": {"$addToSet": "$category"},
                "statuses": {"$addToSet": "$status"}
            }
        },
        {"$match": {"count": {"$gte": 3}}},  # At least 3 issues
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    
    hotspots = []
    for spot in db.issues.aggregate(pipeline):
        hotspots.append({
            "location": {
                "lat": spot["_id"]["lat"] / 100,
                "lng": spot["_id"]["lng"] / 100
            },
            "issueCount": spot["count"],
            "categories": spot["categories"],
            "statuses": spot["statuses"]
        })
    
    return jsonify(hotspots)

@nearby_bp.post("/subscribe-area")
@auth_required()
def subscribe_to_area():
    """Subscribe to notifications for issues in an area"""
    
    data = request.get_json() or {}
    
    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
        radius = float(data.get("radius", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400
    
    user = g.current_user
    
    # Store subscription
    db.area_subscriptions.update_one(
        {"userId": user["_id"]},
        {
            "$set": {
                "location": {"lat": lat, "lng": lng},
                "radius": radius,
                "active": True,
                "updatedAt": datetime.utcnow()
            },
            "$setOnInsert": {
                "createdAt": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return jsonify({"message": "Area subscription updated"})
