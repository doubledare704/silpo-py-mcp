"""OAuth 2.1 + PKCE helpers for the Silpo MCP client.

Wraps FastMCP's ``OAuth`` provider with encrypted on-disk token storage.
Tokens are encrypted at rest with Fernet using a key derived from
``SILPO_OAUTH_ENCRYPTION_KEY`` (auto-generated and persisted on first use).
"""

from __future__ import annotations

import base64
import warnings
from pathlib import Path

from cryptography.fernet import Fernet
from fastmcp.client.auth import OAuth
from key_value.aio.stores.disk import DiskStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

_KEY_FILE = "encryption.key"


class SilpoOAuthError(RuntimeError):
    """Raised when OAuth token storage cannot be initialized."""


def _load_or_create_key(directory: Path) -> str:
    key_file = directory / _KEY_FILE
    if key_file.exists():
        stored = key_file.read_text()
        if not stored.strip():
            raise SilpoOAuthError(f"Empty encryption key file: {key_file}")
        return stored.strip()
    directory.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key().decode()
    key_file.write_text(key)
    try:
        key_file.chmod(0o600)
    except OSError:  # pragma: no cover - platform may not support chmod
        pass
    return key


def _validate_fernet(key: str) -> Fernet:
    try:
        # Fernet expects the urlsafe-base64 encoded key (as returned by
        # Fernet.generate_key()), so we validate against the encoded form.
        base64.urlsafe_b64decode(key)
        return Fernet(key.encode())
    except Exception as exc:
        raise SilpoOAuthError("Invalid Fernet key.") from exc


def build_encrypted_token_storage(
    directory: str | Path,
    encryption_key: str | None = None,
) -> FernetEncryptionWrapper:
    """Create an encrypted on-disk ``AsyncKeyValue`` token store.

    If ``encryption_key`` is provided (base64 urlsafe Fernet key) it is used
    verbatim; otherwise a key is auto-generated and persisted next to the
    token store for symmetric round-trips.
    """
    path = Path(directory).expanduser()
    if encryption_key is not None:
        key = encryption_key
    else:
        key = _load_or_create_key(path)
    fernet = _validate_fernet(key)
    return FernetEncryptionWrapper(
        key_value=DiskStore(directory=str(path)),
        fernet=fernet,
    )


def build_oauth(
    mcp_url: str,
    *,
    scopes: str | list[str] | None = None,
    client_name: str = "silpo-mcp",
    token_endpoint_auth_method: str = "none",
    token_storage: FernetEncryptionWrapper | None = None,
    callback_port: int | None = None,
    callback_timeout: float = 300.0,
) -> OAuth:
    """Build a FastMCP ``OAuth`` provider for the Silpo server.

    Uses the provided (encrypted) token storage, or falls back to in-memory
    storage with a warning when no storage is configured. The DCR request
    explicitly asks for ``token_endpoint_auth_method`` (default ``none``, a
    public client with PKCE) so the authorization server does not register a
    confidential client that would break the ``mcp`` library's token request.
    """
    if token_storage is None:
        warnings.warn(
            "Using in-memory OAuth token storage -- tokens are lost on restart. "
            "Pass an encrypted storage via build_encrypted_token_storage().",
            stacklevel=2,
        )
    return OAuth(
        mcp_url=mcp_url,
        scopes=scopes,
        client_name=client_name,
        additional_client_metadata={"token_endpoint_auth_method": token_endpoint_auth_method},
        token_storage=token_storage,
        callback_port=callback_port,
        callback_timeout=callback_timeout,
    )


__all__ = [
    "SilpoOAuthError",
    "build_encrypted_token_storage",
    "build_oauth",
]
