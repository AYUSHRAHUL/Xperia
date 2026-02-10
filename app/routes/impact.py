from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, g

from .. import db
from ..middleware.auth import auth_required


impact_bp = Blueprint("impact", __name__)


@impact_bp.get("/global")
def global_impact():
    agg = db.global_aggregates.find_one({}) or {}
    return jsonify(
        {
            "totalWaterSaved": agg.get("totalWaterSaved", 0),
            "totalCo2Reduced": agg.get("totalCo2Reduced", 0),
            "totalWasteRemoved": agg.get("totalWasteRemoved", 0),
            "totalFuelSaved": agg.get("totalFuelSaved", 0),
            "totalIssuesResolved": agg.get("totalIssuesResolved", 0),
            "citizenParticipationRate": agg.get("citizenParticipationCount", 0),
        }
    )


@impact_bp.get("/user")
@auth_required()
def user_impact():
    user = g.current_user
    user_id = user["_id"]
    issues = list(db.issues.find({"reportedBy": user_id}))
    issue_ids = [i["_id"] for i in issues]
    metrics = list(db.impact_metrics.find({"issueId": {"$in": issue_ids}}))

    totals = {
        "waterSaved": 0,
        "co2Reduced": 0,
        "wasteRemoved": 0,
        "fuelSaved": 0,
        "safetyScore": 0,
    }
    for m in metrics:
        for k in totals:
            totals[k] += m.get(k, 0)

    return jsonify(
        {
            "totals": totals,
            "points": user.get("points", 0),
        }
    )


@impact_bp.get("/monthly")
def monthly_impact():
    # simple monthly aggregation by createdAt of issues
    pipeline = [
        {
            "$lookup": {
                "from": "impact_metrics",
                "localField": "_id",
                "foreignField": "issueId",
                "as": "metrics",
            }
        },
        {"$unwind": "$metrics"},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$createdAt"},
                    "month": {"$month": "$createdAt"},
                },
                "waterSaved": {"$sum": "$metrics.waterSaved"},
                "co2Reduced": {"$sum": "$metrics.co2Reduced"},
                "wasteRemoved": {"$sum": "$metrics.wasteRemoved"},
                "fuelSaved": {"$sum": "$metrics.fuelSaved"},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    rows = list(db.issues.aggregate(pipeline))
    formatted = []
    for r in rows:
        formatted.append(
            {
                "year": r["_id"]["year"],
                "month": r["_id"]["month"],
                "waterSaved": r.get("waterSaved", 0),
                "co2Reduced": r.get("co2Reduced", 0),
                "wasteRemoved": r.get("wasteRemoved", 0),
                "fuelSaved": r.get("fuelSaved", 0),
            }
        )
    return jsonify(formatted)


@impact_bp.get("/leaderboard")
def leaderboard():
    """Top users by points for gamification/leaderboard views."""
    cursor = db.users.find({}, {"name": 1, "points": 1, "role": 1}).sort("points", -1).limit(20)
    rows = []
    for u in cursor:
        points = u.get("points", 0)
        if points <= 50:
            level = "Beginner"
        elif points <= 150:
            level = "Contributor"
        elif points <= 300:
            level = "Guardian"
        else:
            level = "City Hero"
        rows.append(
            {
                "id": str(u["_id"]),
                "name": u.get("name"),
                "role": u.get("role"),
                "points": points,
                "level": level,
            }
        )
    return jsonify(rows)

