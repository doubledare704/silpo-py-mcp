"""Tests for the Silpo mock server: tool inventory and behavior."""

from __future__ import annotations

from fastmcp import Client

from silpo_py_mcp import SilpoMockServer
from silpo_py_mcp.tools import SilpoTool

EXPECTED_TOOLS: list[str] = [t.value for t in SilpoTool]


async def test_mock_exposes_all_40_documented_tools(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        names = sorted(tool.name for tool in await client.list_tools())
    assert len(names) == 40
    assert names == sorted(EXPECTED_TOOLS)


async def test_mock_get_products_filters(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        result = await client.call_tool("silpo_get_products", {"query": "молоко"})
        assert result.data["total"] == 1
        assert result.data["items"][0]["productId"] == "prd-milk-2pct"

        on_sale = await client.call_tool("silpo_get_products", {"onSale": True})
        assert on_sale.data["total"] == 2


async def test_mock_cart_lifecycle(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        summary = await client.call_tool("silpo_get_my_shopping_cart", {})
        cart_id = summary.data["cartId"]

        add = await client.call_tool(
            "silpo_add_or_update_cart_products",
            {
                "cartId": cart_id,
                "items": [{"productId": "prd-milk-2pct", "quantity": 2}],
            },
        )
        assert add.data["cart"]["totals"]["totalPrice"] == 2 * 36.9

        remove = await client.call_tool(
            "silpo_remove_cart_products", {"cartId": cart_id, "productIds": ["prd-milk-2pct"]}
        )
        assert remove.data["cart"]["items"] == []

        clear = await client.call_tool("silpo_clear_shopping_cart", {"cartId": cart_id})
        assert clear.data["cart"]["totals"]["totalPrice"] == 0.0


async def test_mock_apply_bonuses(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        summary = await client.call_tool("silpo_get_my_shopping_cart", {})
        cart_id = summary.data["cartId"]
        await client.call_tool(
            "silpo_add_or_update_cart_products",
            {
                "cartId": cart_id,
                "items": [{"productId": "prd-cheese", "quantity": 1}],
            },
        )
        updated = await client.call_tool("silpo_update_shopping_cart", {"cartId": cart_id, "bonusRequested": 50.0})
        assert updated.data["cart"]["loyalty"]["bonusApplied"] == 50.0
        assert updated.data["cart"]["totals"]["totalPrice"] == 89.0 - 50.0


async def test_mock_create_shopping_cart_is_idempotent(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        args: dict[str, object] = {
            "addressType": "house",
            "latitude": 50.3957,
            "longitude": 30.6217,
            "deliveryType": "DeliveryHome",
            "branchId": "bran-1",
            "timeslot": {"start": "2026-09-06T10:00:00+03:00", "end": "2026-09-06T11:00:00+03:00"},
            "city": "Київ",
            "street": "вул. Анни Ахматової",
            "house": "9",
        }
        first = await client.call_tool("silpo_create_shopping_cart", args)
        assert first.data["success"] is True
        assert first.data["shoppingCartId"]

        second = await client.call_tool("silpo_create_shopping_cart", args)
        assert second.data["shoppingCartId"] == first.data["shoppingCartId"]

        fetched = await client.call_tool(
            "silpo_get_shopping_cart_by_id", {"shoppingCartId": first.data["shoppingCartId"]}
        )
        assert fetched.data["branchId"] == "bran-1"
        assert fetched.data["deliveryType"] == "DeliveryHome"
