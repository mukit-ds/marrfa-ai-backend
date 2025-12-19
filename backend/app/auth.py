# backend/app/auth.py
import hashlib
from datetime import datetime
from typing import Dict, Any
from fastapi import HTTPException


def hash_password(password: str):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def check_and_update_limit(session_id: str, usage_col) -> bool:
    if not session_id: return True
    user = usage_col.find_one({"session_id": session_id})
    if not user:
        usage_col.insert_one({"session_id": session_id, "count": 1, "first_seen": datetime.now()})
        return True
    if user["count"] >= 3:
        return False
    usage_col.update_one({"session_id": session_id}, {"$inc": {"count": 1}})
    return True


def handle_signup(username: str, email: str, phone: str, password: str, users_col) -> Dict[str, Any]:
    """Handle user signup."""
    if users_col.find_one({"$or": [{"username": username}, {"email": email}]}):
        raise HTTPException(status_code=400, detail="User already exists")
    users_col.insert_one({
        "username": username, "email": email, "phone": phone,
        "password": hash_password(password), "created_at": datetime.now()
    })
    return {"message": "Success"}


def handle_login(identifier: str, password: str, users_col) -> Dict[str, Any]:
    """Handle user login."""
    hashed = hash_password(password)
    user = users_col.find_one({"$or": [{"username": identifier}, {"email": identifier}], "password": hashed})
    if user:
        return {"success": True, "user": {"username": user["username"], "email": user["email"]}}
    raise HTTPException(status_code=401, detail="Invalid credentials")