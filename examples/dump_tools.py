#!/usr/bin/env python3
"""Dump the live ``tools/list`` contract of the Silpo MCP server to JSON.

Run:  uv run examples/dump_tools.py [output.json]
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from silpo_py_mcp import SilpoClient


async def main() -> int:
    out_path = Path(sys.argv[1] if len(sys.argv) > 1 else "live_tools.json")
    async with SilpoClient.for_real_server() as client:
        tools = await client.list_tools()
        payload: list[dict[str, Any]] = [
            {"name": tool.name, "description": tool.description, "inputSchema": tool.inputSchema} for tool in tools
        ]
        await asyncio.to_thread(
            out_path.write_text,
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"wrote {len(payload)} tools to {out_path}")
        for tool in tools:
            schema = tool.inputSchema or {}
            props = schema.get("properties", {})
            required = set(schema.get("required", []))
            parts = [f"{arg}:{prop.get('type', '?')}" + ("!" if arg in required else "") for arg, prop in props.items()]
            print(f"  {tool.name}({', '.join(parts)})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
