import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify(encoded: str | None, password: str) -> bool:
    try:
        valid = hasher.verify(encoded or DUMMY_HASH, password)
        return bool(encoded) and valid
    except (VerificationError, InvalidHashError):
        return False
