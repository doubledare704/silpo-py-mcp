"""Runtime configuration for the Silpo MCP client.

Configuration is read from environment variables (prefixed ``SILPO_``) and an
optional ``.env`` file. All values can be overridden programmatically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SILPO_MCP_URL = "https://mcp.silpo.ua/mcp"


class SilpoSettings(BaseSettings):
    """Settings for the Silpo MCP client.

    Environment variables (prefixed ``SILPO_``) and a ``.env`` file are read
    automatically. Examples: ``SILPO_MCP_URL``, ``SILPO_OAUTH_STORAGE_DIR``,
    ``SILPO_OAUTH_ENCRYPTION_KEY``.
    """

    mcp_url: str = SILPO_MCP_URL
    """Streamable HTTP endpoint of the official Silpo MCP server."""

    oauth_scopes: str | None = Field(default=None, description="OAuth scopes to request.")
    oauth_client_name: str = "silpo-py-mcp"
    oauth_token_endpoint_auth_method: str = "none"
    """Token endpoint auth method for DCR. Silpo supports
    ``none`` (public client + PKCE), ``client_secret_post``, ``client_secret_basic``."""
    oauth_callback_port: int | None = Field(default=None, description="Fixed OAuth callback port (default: random).")
    oauth_callback_timeout: float = 300.0

    oauth_storage_dir: Path = Path("~/.silpo_py_mcp").expanduser()
    """Directory for the encrypted OAuth token store."""

    oauth_encryption_key: str | None = Field(
        default=None,
        description="Fernet key (urlsafe base64) for token encryption. Auto-generated and persisted if omitted.",
    )

    token_expiry_skew: float = 60.0
    """Seconds subtracted from token expiry when deciding to refresh early."""

    default_request_timeout: float = 30.0
    """Default per-request timeout in seconds."""

    max_rate_limit_retries: int = 3
    """Maximum retries with exponential backoff on HTTP 429."""

    rate_limit_backoff_factor: float = 1.0
    """Multiplier for exponential backoff base wait on 429s."""

    model_config = SettingsConfigDict(
        env_prefix="SILPO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def build_settings(**overrides: Any) -> SilpoSettings:
    """Create settings, applying keyword overrides on top of env/.env values."""
    return SilpoSettings(**overrides)
