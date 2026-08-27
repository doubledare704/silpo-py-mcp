"""Tests for error mapping and payload extraction."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.client.client import CallToolResult
from fastmcp.exceptions import ToolError
from mcp.types import ContentBlock, TextContent

from silpo_py_mcp.client import SilpoClient, _extract_payload
from silpo_py_mcp.exceptions import (
    SilpoAuthError,
    SilpoForbiddenError,
    SilpoRateLimitError,
    SilpoToolExecutionError,
    SilpoToolNotFoundError,
)


def _result(*, data: Any = None, text: str | None = None, is_error: bool = False) -> CallToolResult:
    content: list[ContentBlock] = [TextContent(type="text", text=text)] if text is not None else []
    return CallToolResult(
        content=content,
        structured_content=None,
        meta=None,
        data=data,
        is_error=is_error,
    )


class _FakeFastMCP:
    """Minimal stand-in for fastmcp.Client capturing tool calls."""

    def __init__(self, *, raise_error: Exception | None = None, result: CallToolResult | None = None) -> None:
        self._raise_error = raise_error
        self._result = result or _result(data={"ok": True})
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> _FakeFastMCP:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def list_tools(self) -> list[Any]:
        return []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        self.calls.append((name, arguments))
        if self._raise_error is not None:
            raise self._raise_error
        return self._result


def _client(fastmcp: _FakeFastMCP) -> SilpoClient:
    return SilpoClient(fastmcp)  # type: ignore[arg-type]


async def test_call_tool_passes_args_through() -> None:
    fake = _FakeFastMCP()
    client = _client(fake)
    await client.call_tool("silpo_get_products", {"query": "сир", "pageSize": 10})
    assert fake.calls == [("silpo_get_products", {"query": "сир", "pageSize": 10})]


async def test_maps_method_not_found() -> None:
    fake = _FakeFastMCP(raise_error=ToolError("Unknown tool: 'silpo_nope'"))
    with pytest.raises(SilpoToolNotFoundError):
        await _client(fake).call_tool("silpo_nope", {})


async def test_maps_auth_error() -> None:
    fake = _FakeFastMCP(raise_error=ToolError("401 invalid_token"))
    with pytest.raises(SilpoAuthError):
        await _client(fake).call_tool("silpo_get_products", {})


async def test_maps_forbidden_error() -> None:
    fake = _FakeFastMCP(raise_error=ToolError("403 forbidden"))
    with pytest.raises(SilpoForbiddenError):
        await _client(fake).call_tool("silpo_get_products", {})


async def test_maps_rate_limit() -> None:
    fake = _FakeFastMCP(raise_error=ToolError("429 too many requests"))
    with pytest.raises(SilpoRateLimitError):
        await _client(fake).call_tool("silpo_get_products", {})


async def test_surfaces_is_error_results() -> None:
    fake = _FakeFastMCP(result=_result(text="boom", is_error=True))
    with pytest.raises(SilpoToolExecutionError):
        await _client(fake).call_tool("silpo_get_products", {})


def test_extract_payload_prefers_data() -> None:
    assert _extract_payload(_result(data={"a": 1})) == {"a": 1}


def test_extract_payload_unwraps_dataclass_root() -> None:
    from dataclasses import dataclass

    @dataclass
    class _Nested:
        slug: str

    @dataclass
    class _Root:
        success: bool
        items: list[_Nested]

    root = _Root(success=True, items=[_Nested(slug="syr-1")])
    assert _extract_payload(_result(data=root)) == {
        "success": True,
        "items": [{"slug": "syr-1"}],
    }


def test_extract_payload_parses_json_text() -> None:
    result = _result(text='{"x": 2}')
    assert _extract_payload(result) == {"x": 2}


def test_extract_payload_returns_text_when_not_json() -> None:
    result = _result(text="plain")
    assert _extract_payload(result) == "plain"


async def test_extract_payload_raises_when_empty() -> None:
    from silpo_py_mcp.exceptions import SilpoValidationError

    with pytest.raises(SilpoValidationError):
        _extract_payload(_result())
