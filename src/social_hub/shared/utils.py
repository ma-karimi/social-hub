import hashlib
import secrets
import base64
from uuid import UUID


def hash_api_key(api_key: str) -> str:
    """One-way hash of an API key for safe storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(prefix: str = "sh_live_") -> str:
    """Generate a cryptographically secure API key."""
    token = secrets.token_urlsafe(32)
    return f"{prefix}{token}"


def encode_short_id(uid: UUID) -> str:
    """Encode UUID bytes to an 11-char URL-safe base64 short ID."""
    encoded = base64.urlsafe_b64encode(uid.bytes).decode().rstrip("=")
    return encoded[:11]
