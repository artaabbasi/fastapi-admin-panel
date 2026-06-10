"""
Password hashing and JWT utilities.

Dependencies (added to pyproject.toml):
  passlib[bcrypt]
  PyJWT
"""

from __future__ import annotations

import datetime
from typing import Optional

try:
    import jwt
except ImportError:
    raise ImportError("PyJWT is required: pip install PyJWT")

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    raise ImportError("passlib[bcrypt] is required: pip install 'passlib[bcrypt]'")

_ALGORITHM = "HS256"


# ── Passwords ─────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(user_id: int, username: str, secret: str, expire_hours: int) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=expire_hours),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_token(token: str, secret: str) -> Optional[dict]:
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
