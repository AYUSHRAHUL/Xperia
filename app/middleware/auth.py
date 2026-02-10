from functools import wraps

from bson import ObjectId
from flask import request, jsonify, g

from .. import db
from ..utils.security import decode_token


def auth_required(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Authorization header missing"}), 401

            token = auth_header.split(" ", 1)[1]
            try:
                payload = decode_token(token)
            except Exception:
                return jsonify({"error": "Invalid or expired token"}), 401

            user = db.users.find_one({"_id": ObjectId(payload["sub"])})
            if not user:
                return jsonify({"error": "User not found"}), 401

            if roles and user.get("role") not in roles:
                return jsonify({"error": "Forbidden"}), 403

            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


