from datetime import datetime

from .. import db
from bson import ObjectId


def calculate_impact(issue: dict, closed_at: datetime):
    reported_at = issue.get("createdAt") or issue.get("reportedAt")
    if isinstance(reported_at, str):
        reported_at = datetime.fromisoformat(reported_at)
    duration_hours = (closed_at - reported_at).total_seconds() / 3600 if reported_at else 0

    category = issue.get("category")
    impact = {
        "waterSaved": 0,
        "wasteRemoved": 0,
        "co2Reduced": 0,
        "fuelSaved": 0,
        "safetyScore": 0,
    }

    if category == "Water Leakage":
        liters_per_minute = 15
        water_saved = liters_per_minute * 60 * duration_hours
        impact["waterSaved"] = round(water_saved, 2)

    if category == "Garbage Dump":
        avg_weight = 25  # kg
        impact["wasteRemoved"] = avg_weight
        impact["co2Reduced"] = round(avg_weight * 0.8, 2)

    if category == "Pothole":
        # treat as emission reduction proxy
        impact["co2Reduced"] = round(10 * duration_hours, 2)

    if category == "Traffic Signal Failure":
        impact["fuelSaved"] = round(0.3 * duration_hours, 2)

    if category == "Broken Streetlight":
        impact["safetyScore"] = 10

    return impact


def persist_impact(issue_id: ObjectId, impact: dict, user_id: ObjectId | None = None):
    metrics_doc = {
        "issueId": issue_id,
        **impact,
    }
    db.impact_metrics.insert_one(metrics_doc)

    # Update global aggregates (single document pattern)
    agg = db.global_aggregates.find_one({}) or {
        "totalWaterSaved": 0,
        "totalCo2Reduced": 0,
        "totalWasteRemoved": 0,
        "totalFuelSaved": 0,
        "totalIssuesResolved": 0,
        "citizenParticipationCount": 0,
    }
    agg["totalWaterSaved"] += impact.get("waterSaved", 0)
    agg["totalCo2Reduced"] += impact.get("co2Reduced", 0)
    agg["totalWasteRemoved"] += impact.get("wasteRemoved", 0)
    agg["totalFuelSaved"] += impact.get("fuelSaved", 0)
    agg["totalIssuesResolved"] += 1

    db.global_aggregates.replace_one({}, agg, upsert=True)


