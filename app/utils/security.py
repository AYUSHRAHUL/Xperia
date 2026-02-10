import datetime
import os

import bcrypt
import jwt


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(password: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except ValueError:
        return False


def create_access_token(user_id: str, role: str, expires_minutes: int = 60) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes),
    }
    secret = os.getenv("JWT_SECRET", "jwt-secret")
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str):
    secret = os.getenv("JWT_SECRET", "jwt-secret")
    return jwt.decode(token, secret, algorithms=["HS256"])


