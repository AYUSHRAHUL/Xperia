from datetime import datetime
from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required

votes_bp = Blueprint("votes", __name__)

@votes_bp.post("/<issue_id>/upvote")
@auth_required()
def upvote_issue(issue_id):
    """Upvote an issue to increase its priority"""
    try:
        oid = ObjectId(issue_id)
    except:
        return jsonify({"error": "Invalid issue ID"}), 400
    
    # Verify issue exists
    issue = db.issues.find_one({"_id": oid})
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    
    user = g.current_user
    
    # Check if already voted
    existing_vote = db.votes.find_one({"issueId": oid, "userId": user["_id"]})
    if existing_vote:
        return jsonify({"error": "Already voted"}), 400
    
    # Add vote
    db.votes.insert_one({
        "issueId": oid,
        "userId": user["_id"],
        "createdAt": datetime.utcnow()
    })
    
    # Get updated vote count
    vote_count = db.votes.count_documents({"issueId": oid})
    
    return jsonify({
        "message": "Vote recorded",
        "voteCount": vote_count
    })

@votes_bp.delete("/<issue_id>/upvote")
@auth_required()
def remove_upvote(issue_id):
    """Remove upvote from an issue"""
    try:
        oid = ObjectId(issue_id)
    except:
        return jsonify({"error": "Invalid issue ID"}), 400
    
    user = g.current_user
    
    result = db.votes.delete_one({"issueId": oid, "userId": user["_id"]})
    
    if result.deleted_count == 0:
        return jsonify({"error": "Vote not found"}), 404
    
    # Get updated vote count
    vote_count = db.votes.count_documents({"issueId": oid})
    
    return jsonify({
        "message": "Vote removed",
        "voteCount": vote_count
    })

@votes_bp.get("/<issue_id>/votes")
def get_vote_count(issue_id):
    """Get vote count and user's vote status"""
    try:
        oid = ObjectId(issue_id)
    except:
        return jsonify({"error": "Invalid issue ID"}), 400
    
    vote_count = db.votes.count_documents({"issueId": oid})
    
    # Check if current user has voted (if authenticated)
    user_voted = False
    if hasattr(g, 'current_user') and g.current_user:
        user_voted = db.votes.find_one({"issueId": oid, "userId": g.current_user["_id"]}) is not None
    
    return jsonify({
        "voteCount": vote_count,
        "userVoted": user_voted
    })

@votes_bp.get("/top-voted")
def get_top_voted_issues():
    """Get issues sorted by vote count"""
    limit = int(request.args.get("limit", 10))
    
    # Aggregate to count votes per issue
    pipeline = [
        {
            "$group": {
                "_id": "$issueId",
                "voteCount": {"$sum": 1}
            }
        },
        {"$sort": {"voteCount": -1}},
        {"$limit": limit}
    ]
    
    vote_results = list(db.votes.aggregate(pipeline))
    
    # Get issue details
    issues = []
    for vote_data in vote_results:
        issue = db.issues.find_one({"_id": vote_data["_id"]})
        if issue:
            issues.append({
                "id": str(issue["_id"]),
                "title": issue["title"],
                "category": issue["category"],
                "status": issue["status"],
                "voteCount": vote_data["voteCount"],
                "createdAt": issue["createdAt"].isoformat()
            })
    
    return jsonify(issues)
