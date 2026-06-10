"""FastAPI dependency that enforces JWT authentication on admin routes."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .utils import decode_token

_bearer = HTTPBearer(auto_error=False)


def make_require_admin(secret_key: str):
    """
    Returns a FastAPI dependency that validates the Bearer token.
    Call once at startup and reuse the returned dependency.
    """

    def require_admin(
        creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> dict:
        if creds is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = decode_token(creds.credentials, secret_key)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload

    return require_admin


# Placeholder — replaced by make_require_admin() at panel init time
require_admin = make_require_admin("__unset__")
