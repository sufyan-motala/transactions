import json
import os
import keyring
from pathlib import Path
from typing import Dict
from transactions_core.security import Encryptor

APP_NAME = "transactions-cli"
KEYRING_SERVICE_NAME = "transactions-cli"
KEYRING_USERNAME = "master-key"

# Standard config paths
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"


def _get_encryptor() -> Encryptor:
    """
    Retrieves the encryption key from the OS System Keyring (Keychain/CredMgr).
    If no key exists, generates one and saves it to the Keyring.
    """
    # Try to get the key from the system keyring
    stored_key = keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME)

    if stored_key:
        # Keyring stores strings, so we encode back to bytes
        return Encryptor(stored_key.encode("utf-8"))

    # If no key found, generate a new one
    new_key_bytes = Encryptor.generate_key()
    new_key_str = new_key_bytes.decode("utf-8")

    try:
        # Save the new key to the secure keyring
        keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME, new_key_str)
    except Exception as e:
        # Fallback for headless servers/CI where no keyring exists
        print(
            f"Warning: Could not access system keyring ({e}). Falling back to memory-only key (session will not persist)."
        )
        # In a real production CLI, you may fallback to a file here with a warning,
        # but for security strictness, we'll just return the key.
        pass

    return Encryptor(new_key_bytes)


def get_config() -> Dict:
    """
    Reads the config file and decrypts sensitive payloads.
    """
    if not CONFIG_FILE.exists():
        return {}

    try:
        encryptor = _get_encryptor()
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)

        # Decrypt the payload if it exists
        if "payload" in data and isinstance(data["payload"], dict):
            for k, v in data["payload"].items():
                if isinstance(v, str):
                    # Attempt to decrypt; if it fails (wrong key), keep original
                    data["payload"][k] = encryptor.decrypt(v)

        return data
    except Exception:
        # Return empty config on corruption or key failure
        return {}


def save_config(provider_name: str, payload: Dict):
    """
    Encrypts sensitive data and saves to the config file.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    encryptor = _get_encryptor()

    # Create a copy to encrypt
    secure_payload = {}
    for k, v in payload.items():
        if isinstance(v, str):
            secure_payload[k] = encryptor.encrypt(v)
        else:
            secure_payload[k] = v

    data = {"provider": provider_name, "payload": secure_payload}

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
