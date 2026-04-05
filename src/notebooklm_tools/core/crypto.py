"""Cookie encryption utilities for NotebookLM MCP CLI.

Provides Fernet-based encryption for cookies.json with a key derivation
fallback chain:
1. keyring (if installed) — stores/retrieves a random Fernet key
2. Machine-id derived key via PBKDF2HMAC (Linux/macOS)
3. Plaintext fallback with warning
"""

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_SERVICE_NAME = "notebooklm-mcp-cli"
_KEY_ACCOUNT = "cookie-encryption-key"
_PBKDF2_SALT = b"notebooklm-mcp-cli-cookie-enc"
_PBKDF2_ITERATIONS = 480_000


def _get_machine_id() -> str | None:
    """Read machine-id from standard Linux/macOS locations."""
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            mid = Path(path).read_text().strip()
            if mid:
                return mid
        except OSError:
            continue
    # macOS: use IOPlatformSerialNumber via system_profiler is complex;
    # fall back to hostname as last resort
    hostname = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME")
    return hostname or None


def _derive_key_from_machine_id(machine_id: str) -> bytes:
    """Derive a Fernet key from machine-id using PBKDF2."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_PBKDF2_SALT,
        iterations=_PBKDF2_ITERATIONS,
    )
    raw = kdf.derive(machine_id.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def get_encryption_key() -> bytes | None:
    """Get or create an encryption key for cookie storage.

    Returns a 32-byte url-safe base64-encoded key suitable for Fernet,
    or None if no key source is available (plaintext fallback).
    """
    # 1. Try keyring
    try:
        import keyring

        stored = keyring.get_password(_SERVICE_NAME, _KEY_ACCOUNT)
        if stored:
            return stored.encode("ascii")
        # Generate and store a new key
        from cryptography.fernet import Fernet

        new_key = Fernet.generate_key()
        keyring.set_password(_SERVICE_NAME, _KEY_ACCOUNT, new_key.decode("ascii"))
        logger.debug("Generated and stored new encryption key in keyring")
        return new_key
    except Exception:
        logger.debug("Keyring not available, trying machine-id derivation")

    # 2. Try machine-id derivation
    machine_id = _get_machine_id()
    if machine_id:
        try:
            key = _derive_key_from_machine_id(machine_id)
            logger.debug("Derived encryption key from machine-id")
            return key
        except Exception as e:
            logger.debug(f"Machine-id key derivation failed: {e}")

    # 3. No key available
    return None


def encrypt_data(plaintext: str, key: bytes) -> bytes:
    """Encrypt a string using Fernet. Returns encrypted bytes."""
    from cryptography.fernet import Fernet

    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_data(token: bytes, key: bytes) -> str:
    """Decrypt Fernet-encrypted bytes back to a string."""
    from cryptography.fernet import Fernet

    f = Fernet(key)
    return f.decrypt(token).decode("utf-8")


def is_encrypted(data: bytes) -> bool:
    """Check if data looks like a Fernet token (starts with 'gAAAAA')."""
    return data.startswith(b"gAAAAA")
