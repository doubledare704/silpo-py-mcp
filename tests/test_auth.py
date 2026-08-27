"""Tests for encrypted OAuth token storage."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from key_value.aio.adapters.pydantic import PydanticAdapter
from mcp.shared.auth import OAuthToken

from silpo_mcp.auth import (
    SilpoOAuthError,
    build_encrypted_token_storage,
    build_oauth,
)


async def test_storage_roundtrip(tmp_path: Path) -> None:
    store = build_encrypted_token_storage(tmp_path)
    adapter = PydanticAdapter[OAuthToken](
        default_collection="mcp-oauth-token",
        key_value=store,
        pydantic_model=OAuthToken,
        raise_on_validation_error=True,
    )
    token = OAuthToken(
        access_token="access-token",
        token_type="bearer",
        expires_in=3600,
        refresh_token="refresh-token",
    )
    await adapter.put(key="https://mcp.silpo.ua/mcp/tokens", value=token)

    restored = await adapter.get(key="https://mcp.silpo.ua/mcp/tokens")
    assert restored is not None
    assert restored.access_token == "access-token"
    assert restored.refresh_token == "refresh-token"


async def test_storage_is_encrypted_at_rest(tmp_path: Path) -> None:
    store = build_encrypted_token_storage(tmp_path)
    adapter = PydanticAdapter[OAuthToken](
        default_collection="mcp-oauth-token",
        key_value=store,
        pydantic_model=OAuthToken,
        raise_on_validation_error=True,
    )
    await adapter.put(
        key="https://mcp.silpo.ua/mcp/tokens",
        value=OAuthToken(access_token="secret-value", token_type="bearer"),
    )

    on_disk = next(tmp_path.rglob("*.db"))
    raw = on_disk.read_bytes()
    assert b"secret-value" not in raw


async def test_storage_reuses_persisted_key(tmp_path: Path) -> None:
    # The key file is created on first use and reused on the second,
    # so tokens written through one store are readable through another.
    first = build_encrypted_token_storage(tmp_path)
    adapter = PydanticAdapter[OAuthToken](
        default_collection="mcp-oauth-token",
        key_value=first,
        pydantic_model=OAuthToken,
        raise_on_validation_error=True,
    )
    await adapter.put(
        key="https://mcp.silpo.ua/mcp/tokens",
        value=OAuthToken(access_token="persisted", token_type="bearer"),
    )

    second = build_encrypted_token_storage(tmp_path)
    adapter2 = PydanticAdapter[OAuthToken](
        default_collection="mcp-oauth-token",
        key_value=second,
        pydantic_model=OAuthToken,
        raise_on_validation_error=True,
    )
    restored = await adapter2.get(key="https://mcp.silpo.ua/mcp/tokens")
    assert restored is not None
    assert restored.access_token == "persisted"


def test_storage_accepts_explicit_key(tmp_path: Path) -> None:
    key = Fernet.generate_key().decode()
    store = build_encrypted_token_storage(tmp_path, encryption_key=key)
    assert store is not None


def test_storage_accepts_str_path() -> None:
    store = build_encrypted_token_storage(str(Path("/tmp") / "silpo-auth-str"))
    assert store is not None


def test_storage_rejects_invalid_key(tmp_path: Path) -> None:
    with pytest.raises(SilpoOAuthError):
        build_encrypted_token_storage(tmp_path, encryption_key="not-a-valid-key")


def test_build_oauth_sets_public_client_auth_method() -> None:
    oauth = build_oauth("https://mcp.silpo.ua/mcp", client_name="silpo-mcp")
    assert oauth.context.client_metadata.token_endpoint_auth_method == "none"


def test_build_oauth_allows_auth_method_override() -> None:
    oauth = build_oauth("https://mcp.silpo.ua/mcp", token_endpoint_auth_method="client_secret_post")
    assert oauth.context.client_metadata.token_endpoint_auth_method == "client_secret_post"
