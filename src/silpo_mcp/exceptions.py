"""Typed exceptions raised by the Silpo MCP client."""

from __future__ import annotations


class SilpoError(Exception):
    """Base error for all Silpo MCP client failures."""


class SilpoConnectionError(SilpoError):
    """Raised when the client cannot connect to or initialize the MCP server."""


class SilpoAuthError(SilpoError):
    """Raised when authentication fails or tokens are invalid/expired.

    Maps to the Silpo ``401 invalid_token`` response — the caller should
    re-run the OAuth flow or refresh the token.
    """


class SilpoForbiddenError(SilpoError):
    """Raised when the token is valid but lacks access to a tool (HTTP 403)."""


class SilpoRateLimitError(SilpoError):
    """Raised when the server rate-limits the request (HTTP 429).

    Carries optional ``retry_after`` seconds from the server. Silpo applies
    rate limits per-user via ``Cookie: mcp-user={userId}``.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SilpoToolNotFoundError(SilpoError):
    """Raised when the server does not support the requested tool (JSON-RPC -32601)."""


class SilpoToolExecutionError(SilpoError):
    """Raised when a tool call itself fails (server-side execution error)."""


class SilpoValidationError(SilpoError):
    """Raised when a server response does not match the expected schema."""
