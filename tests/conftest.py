"""Shared fixtures for the silpo-mcp test suite."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from silpo_mcp import SilpoClient, SilpoMockServer


@pytest.fixture
async def client() -> AsyncGenerator[SilpoClient]:
    """A SilpoClient connected in-memory to a fresh mock server."""
    async with SilpoClient.for_mock() as client:
        yield client


@pytest.fixture
def mock_server() -> SilpoMockServer:
    return SilpoMockServer()
