import hashlib
from config import settings


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256((api_key + settings.api_key_salt).encode()).hexdigest()
