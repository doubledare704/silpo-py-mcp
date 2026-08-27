import asyncio

from silpo_py_mcp import SilpoClient


async def main() -> None:
    async with SilpoClient.for_real_server() as client:
        tools = await client.list_tools()
        print(f"Connected. {len(tools)} tools available.")

        branches = await client.call_tool("silpo_list_branches", {"limit": 1})
        print("Branch:", branches["branches"][0]["address"])


asyncio.run(main())
