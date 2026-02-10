from datetime import datetime
from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required

bulk_bp = Blueprint("bulk", __name__)

@bulk_bp.post("/verify")
@auth_required(roles=["admin"])
def bulk_verify():
    """Verify multiple issues at once"""
    
    data = request.get_json() or {}
    issue_ids = data.get("issueIds", [])
    
    if not issue_ids:
        return jsonify({"error": "No issue IDs provided"}), 400
    
    verified_count = 0
    failed = []
    
    for issue_id in issue_ids:
        try:
            oid = ObjectId(issue_id)
            result = db.issues.update_one(
                {"_id": oid, "status": "REPORTED"},
                {
                    "$set": {
                        "status": "VERIFIED",
                        "updatedAt": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                verified_count += 1
                
                # Add audit log
                db.audit_logs.insert_one({
                    "issueId": oid,
                    "action": "VERIFIED",
                    "performedBy": g.current_user["_id"],
                    "timestamp": datetime.utcnow()
                })
                
                # Notify reporter
                issue = db.issues.find_one({"_id": oid})
                if issue:
                    from .notifications import create_notification
                    create_notification(
                        issue["reportedBy"],
                        "info",
                        "Issue Verified",
                        f"Your issue '{issue['title']}' has been verified"
                    )
            else:
                failed.append(issue_id)
                
        except Exception as e:
            failed.append(issue_id)
    
    return jsonify({
        "verified": verified_count,
        "failed": len(failed),
        "failedIds": failed
    })

@bulk_bp.post("/assign")
@auth_required(roles=["admin"])
def bulk_assign():
    """Assign multiple issues to a worker"""
    
    data = request.get_json() or {}
    issue_ids = data.get("issueIds", [])
    worker_id = data.get("workerId")
    
    if not issue_ids or not worker_id:
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        wid = ObjectId(worker_id)
    except:
        return jsonify({"error": "Invalid worker ID"}), 400
    
    # Verify worker exists
    worker = db.users.find_one({"_id": wid, "role": "worker"})
    if not worker:
        return jsonify({"error": "Worker not found"}), 400
    
    assigned_count = 0
    failed = []
    
    for issue_id in issue_ids:
        try:
            oid = ObjectId(issue_id)
            result = db.issues.update_one(
                {"_id": oid, "status": {"$in": ["VERIFIED", "REPORTED"]}},
                {
                    "$set": {
                        "assignedTo": wid,
                        "status": "ASSIGNED",
                        "updatedAt": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                assigned_count += 1
                
                # Add audit log
                db.audit_logs.insert_one({
                    "issueId": oid,
                    "action": "ASSIGNED",
                    "performedBy": g.current_user["_id"],
                    "timestamp": datetime.utcnow()
                })
                
                # Notify worker and reporter
                issue = db.issues.find_one({"_id": oid})
                if issue:
                    from .notifications import create_notification
                    create_notification(
                        wid,
                        "info",
                        "New Task Assigned",
                        f"You have been assigned: {issue['title']}"
                    )
                    create_notification(
                        issue["reportedBy"],
                        "info",
                        "Issue Assigned",
                        f"A worker has been assigned to your issue"
                    )
            else:
                failed.append(issue_id)
                
        except Exception as e:
            failed.append(issue_id)
    
    return jsonify({
        "assigned": assigned_count,
        "failed": len(failed),
        "failedIds": failed
    })

@bulk_bp.post("/close")
@auth_required(roles=["admin"])
def bulk_close():
    """Close multiple resolved issues"""
    
    data = request.get_json() or {}
    issue_ids = data.get("issueIds", [])
    
    if not issue_ids:
        return jsonify({"error": "No issue IDs provided"}), 400
    
    closed_count = 0
    failed = []
    
    for issue_id in issue_ids:
        try:
            oid = ObjectId(issue_id)
            issue = db.issues.find_one({"_id": oid})
            
            if not issue or issue["status"] != "RESOLVED":
                failed.append(issue_id)
                continue
            
            # Update status
            db.issues.update_one(
                {"_id": oid},
                {
                    "$set": {
                        "status": "CLOSED",
                        "updatedAt": datetime.utcnow()
                    }
                }
            )
            
            closed_count += 1
            
            # Add audit log
            db.audit_logs.insert_one({
                "issueId": oid,
                "action": "CLOSED",
                "performedBy": g.current_user["_id"],
                "timestamp": datetime.utcnow()
            })
            
            # Calculate and persist impact
            from ..utils.impact_engine import calculate_impact, persist_impact
            impact = calculate_impact(issue, datetime.utcnow())
            persist_impact(oid, impact, issue.get("reportedBy"))
            
            # Award points
            db.users.update_one(
                {"_id": issue["reportedBy"]},
                {"$inc": {"points": 20}}
            )
            
            # Notify reporter
            from .notifications import create_notification
            create_notification(
                issue["reportedBy"],
                "success",
                "Issue Closed",
                "Your issue has been closed and points awarded!"
            )
            
        except Exception as e:
            failed.append(issue_id)
    
    return jsonify({
        "closed": closed_count,
        "failed": len(failed),
        "failedIds": failed
    })

@bulk_bp.delete("/issues")
@auth_required(roles=["admin"])
def bulk_delete():
    """Delete multiple issues (spam/duplicates)"""
    
    data = request.get_json() or {}
    issue_ids = data.get("issueIds", [])
    
    if not issue_ids:
        return jsonify({"error": "No issue IDs provided"}), 400
    
    deleted_count = 0
    
    for issue_id in issue_ids:
        try:
            oid = ObjectId(issue_id)
            
            # Delete issue
            result = db.issues.delete_one({"_id": oid})
            
            if result.deleted_count > 0:
                deleted_count += 1
                
                # Clean up related data
                db.audit_logs.delete_many({"issueId": oid})
                db.impact_metrics.delete_many({"issueId": oid})
                db.comments.delete_many({"issueId": oid})
                db.votes.delete_many({"issueId": oid})
                
        except Exception as e:
            continue
    
    return jsonify({
        "deleted": deleted_count
    })
