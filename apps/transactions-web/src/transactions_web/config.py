import os
from pathlib import Path
from transactions_core.security import Encryptor


class Settings:
    # App Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "change-this-in-production-to-a-secure-random-string"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # Persistence
    # Use standard user data directory: ~/.local/share/transactions-web (Linux/Mac)
    APP_NAME = "transactions-web"
    DATA_DIR = (
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        / APP_NAME
    )

    @property
    def DATABASE_URL(self) -> str:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.DATA_DIR}/app.db"

    # Encryption (Derived from SECRET_KEY)
    @property
    def encryptor(self) -> Encryptor:
        return Encryptor.from_secret(self.SECRET_KEY)


settings = Settings()
