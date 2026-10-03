import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hmac
import hashlib
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(DOTENV_PATH, override=True)

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def hash_password(password: str) -> str:
    """Simple SHA-256 hash for backward compatibility."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify hash for backward compatibility."""
    return hash_password(plain_password) == hashed_password


def get_admin_credentials():
    load_dotenv(DOTENV_PATH, override=True)
    username = os.getenv("ADMIN_USERNAME", "admin").strip()
    email = os.getenv("ADMIN_EMAIL", "admin@firebird.internal").strip()
    password = os.getenv("ADMIN_PASSWORD", "AdminSecurePass123!").strip()
    jwt_secret = os.getenv("JWT_SECRET", "super-secret-firebird-jwt-key-2026").strip()
    return {
        "username": username,
        "email": email,
        "password": password,
        "jwt_secret": jwt_secret
    }

def verify_admin_credentials(password: str, username: Optional[str] = None) -> bool:
    """
    Verify admin password and optional username against environment variables.
    Uses timing-safe comparison to prevent timing attacks.
    """
    if not password:
        return False
    creds = get_admin_credentials()
    admin_pass = creds["password"]
    admin_user = creds["username"]
    admin_email = creds["email"]

    # Verify password
    if not hmac.compare_digest(password.strip().encode("utf-8"), admin_pass.encode("utf-8")):
        return False

    # If username provided, ensure it matches either username or email (case-insensitive)
    if username and username.strip():
        u = username.strip().lower()
        if u != admin_user.lower() and u != admin_email.lower():
            return False

    return True

def create_admin_token(expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token for the administrator."""
    creds = get_admin_credentials()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": "admin",
        "role": "ADMIN",
        "name": "System Administrator",
        "username": creds["username"],
        "email": creds["email"],
        "exp": expire,
        "iat": now
    }
    return jwt.encode(payload, creds["jwt_secret"], algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    if not token:
        return None
    creds = get_admin_credentials()
    try:
        payload = jwt.decode(token, creds["jwt_secret"], algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None

def get_optional_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Optional dependency: returns admin payload dict if valid Admin JWT Bearer token is provided.
    Returns None for normal visitors. Never raises an HTTPException.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload or payload.get("role") != "ADMIN":
        return None

    return payload

def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Strict dependency: enforces that the caller has authenticated as ADMIN.
    Raises 401 if token is missing/invalid, or 403 if not ADMIN.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin access required"
        )

    return payload
