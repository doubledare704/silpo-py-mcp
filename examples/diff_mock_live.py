#!/usr/bin/env python3
"""Diff the mock server's tools/list contract against a live dump.

Run:  uv run examples/dump_tools.py /tmp/live_tools.json
      uv run examples/diff_mock_live.py /tmp/live_tools.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client

from silpo_py_mcp.mock_server import SilpoMockServer


async def main() -> None:
    live_path = Path(sys.argv[1])
    raw = await asyncio.to_thread(live_path.read_text, encoding="utf-8")
    live: dict[str, Any] = {tool["name"]: tool for tool in json.loads(raw)}
    server = SilpoMockServer()
    async with Client(server.fastmcp) as client:
        tools = await client.list_tools()
    mock = {tool.name: tool for tool in tools}
    print(f"live: {len(live)}  mock: {len(mock)}")
    print("missing in mock:", sorted(set(live) - set(mock)))
    print("extra in mock:", sorted(set(mock) - set(live)))
    for name in sorted(set(live) & set(mock)):
        live_props = live[name]["inputSchema"].get("properties", {})
        mock_props = mock[name].inputSchema.get("properties", {})
        live_required = set(live[name]["inputSchema"].get("required", []))
        mock_required = set(mock[name].inputSchema.get("required", []))
        live_names = set(live_props)
        mock_names = set(mock_props)
        if live_names == mock_names and live_required == mock_required:
            continue
        print(f"\n{name}")
        print(f"  live props : {sorted(live_names)} required={sorted(live_required)}")
        print(f"  mock props : {sorted(mock_names)} required={sorted(mock_required)}")
        if live_names - mock_names:
            print(f"  live-only args: {sorted(live_names - mock_names)}")
        if mock_names - live_names:
            print(f"  mock-only args: {sorted(mock_names - live_names)}")
        if live_required != mock_required:
            print(
                f"  required diff: live-only={sorted(live_required - mock_required)} "
                f"mock-only={sorted(mock_required - live_required)}"
            )


if __name__ == "__main__":
    asyncio.run(main())
