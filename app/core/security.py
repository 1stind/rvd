"""
Password hashing (Argon2).

Per CLAUDE.md:
- passwords must be hashed with Argon2, never stored plain
- SECRET_KEY must never be exposed to clients or logs
"""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, InvalidHashError):
        return False
