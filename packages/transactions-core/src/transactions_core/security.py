import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Encryptor:
    def __init__(self, key: bytes):
        """
        Initialize with a 32-byte URL-safe base64-encoded key.
        """
        self.fernet = Fernet(key)

    @classmethod
    def from_secret(
        cls, secret: str, salt: bytes = b"transactions-salt"
    ) -> "Encryptor":
        """
        Derive a secure key from a user-provided secret (password/token).
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return cls(key)

    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a new random key."""
        return Fernet.generate_key()

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        try:
            return self.fernet.decrypt(token.encode()).decode()
        except Exception:
            # Fallback: return original data if decryption fails (migration support)
            return token
