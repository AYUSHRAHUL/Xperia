from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from .. import db
from ..middleware.auth import auth_required
from ..utils.security import hash_password, verify_password, create_access_token
from ..utils.email import send_email
import jwt
import os


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "citizen")

    if not all([name, email, password]):
        return jsonify({"error": "Missing fields"}), 400

    existing = db.users.find_one({"email": email})
    if existing:
        return jsonify({"error": "Email already registered"}), 400

    hashed = hash_password(password)
    user_doc = {
        "name": name,
        "email": email,
        "password": hashed,
        "role": role,
        "points": 0,
        "createdAt": datetime.utcnow(),
    }
    res = db.users.insert_one(user_doc)
    user_id = str(res.inserted_id)
    user_id = str(res.inserted_id)
    token = create_access_token(user_id, role)
    
    # Send Welcome Email
    send_email(
        email, 
        "Welcome to Urban Pulse!", 
        f"Hi {name},<br><br>Welcome to Urban Pulse! We're excited to have you join our community of changemakers.<br><br>Start reporting issues and making an impact today!<br><br>Best,<br>The Urban Pulse Team"
    )
    
    return jsonify({"token": token, "user": {"id": user_id, "name": name, "email": email, "role": role}}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Missing credentials"}), 400

    user = db.users.find_one({"email": email})
    if not user or not verify_password(password, user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    user_id = str(user["_id"])
    token = create_access_token(user_id, user["role"])
    return jsonify(
        {
            "token": token,
            "user": {
                "id": user_id,
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "points": user.get("points", 0),
            },
        }
    )


@auth_bp.get("/me")
@auth_required()
def me():
    user = g.current_user
    return jsonify(
        {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "points": user.get("points", 0),
        }
    )


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400
        
    user = db.users.find_one({"email": email})
    if not user:
        return jsonify({"message": "If email exists, reset link sent"}), 200 # Security: don't reveal existence
        
    # Generate reset token (1 hour expiry)
    reset_token = jwt.encode(
        {"id": str(user["_id"]), "role": user["role"], "exp": datetime.utcnow().timestamp() + 3600, "type": "reset"},
        os.getenv("JWT_SECRET"),
        algorithm="HS256"
    )
    
    app_url = os.getenv("APP_URL", "http://localhost:5000")
    link = f"{app_url}/reset-password?token={reset_token}"
    
    send_email(
        email,
        "Reset Your Password",
        f"Hi {user['name']},<br><br>Click the link below to reset your password:<br><a href='{link}'>Reset Password</a><br><br>This link expires in 1 hour."
    )
    
    return jsonify({"message": "Reset link sent"}), 200


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json() or {}
    token = data.get("token")
    new_password = data.get("password")
    
    if not token or not new_password:
        return jsonify({"error": "Missing fields"}), 400
        
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        if payload.get("type") != "reset":
            return jsonify({"error": "Invalid token type"}), 400
            
        user_id = payload["id"]
        hashed = hash_password(new_password)
        
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"password": hashed}})
        
        return jsonify({"message": "Password updated successfully"}), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 400
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 400


@auth_bp.put("/me")
@auth_required()
def update_profile():
    user = g.current_user
    data = request.get_json() or {}
    
    update = {}
    if "name" in data and data["name"].strip():
        update["name"] = data["name"].strip()
    
    if update:
        db.users.update_one({"_id": user["_id"]}, {"$set": update})
        
    return jsonify({"message": "Profile updated successfully"})


@auth_bp.put("/change-password")
@auth_required()
def change_password():
    user = g.current_user
    data = request.get_json() or {}
    old_pass = data.get("oldPassword")
    new_pass = data.get("newPassword")
    
    if not old_pass or not new_pass:
        return jsonify({"error": "Missing fields"}), 400
        
    if not verify_password(old_pass, user["password"]):
        return jsonify({"error": "Incorrect current password"}), 400
        
    if len(new_pass) < 6:
        return jsonify({"error": "New password too short"}), 400
        
    hashed = hash_password(new_pass)
    db.users.update_one({"_id": user["_id"]}, {"$set": {"password": hashed}})
    
    return jsonify({"message": "Password updated successfully"})


