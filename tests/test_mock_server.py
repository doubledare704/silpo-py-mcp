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
        ctx = {
            "branchId": "bran-1",
            "deliveryType": "DeliveryHome",
            "timeslotStart": "2026-09-06T10:00:00+03:00",
            "timeslotEnd": "2026-09-06T11:00:00+03:00",
        }
        result = await client.call_tool("silpo_get_products", {**ctx, "category": "Молочні продукти"})
        assert result.data["total"] == 2
        assert result.data["items"][0]["productId"] == "prd-milk-2pct"
        assert result.data["items"][0]["displayPrice"] == 36.9

        in_stock = await client.call_tool("silpo_get_products", {**ctx, "inStock": True})
        assert in_stock.data["total"] == 4

        priced = await client.call_tool(
            "silpo_get_products", {**ctx, "category": "Молочні продукти", "fromPrice": 30.0, "toPrice": 40.0}
        )
        assert priced.data["total"] == 1
        assert priced.data["items"][0]["productId"] == "prd-milk-2pct"


async def test_mock_cart_lifecycle(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        summary = await client.call_tool("silpo_get_my_shopping_cart", {})
        cart_id = summary.data["cartId"]

        add = await client.call_tool(
            "silpo_add_or_update_cart_products",
            {
                "shoppingCartId": cart_id,
                "products": [{"productId": "prd-milk-2pct", "quantity": 2}],
            },
        )
        assert add.data["cart"]["totals"]["totalPrice"] == 2 * 36.9

        remove = await client.call_tool(
            "silpo_remove_cart_products", {"shoppingCartId": cart_id, "products": [{"productId": "prd-milk-2pct"}]}
        )
        assert remove.data["cart"]["items"] == []

        clear = await client.call_tool("silpo_clear_shopping_cart", {"shoppingCartId": cart_id})
        assert clear.data["cart"]["totals"]["totalPrice"] == 0.0


async def test_mock_apply_bonuses(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        summary = await client.call_tool("silpo_get_my_shopping_cart", {})
        cart_id = summary.data["cartId"]
        await client.call_tool(
            "silpo_add_or_update_cart_products",
            {
                "shoppingCartId": cart_id,
                "products": [{"productId": "prd-cheese", "quantity": 1}],
            },
        )
        updated = await client.call_tool(
            "silpo_update_shopping_cart",
            {
                "shoppingCartId": cart_id,
                "deliveryType": "DeliveryHome",
                "timeslot": {"start": "2026-09-06T10:00:00+03:00", "end": "2026-09-06T11:00:00+03:00"},
                "address": {"address": "Київ, вул. Анни Ахматової, 9"},
                "shipments": [],
                "bonusRequested": 50.0,
            },
        )
        assert updated.data["cart"]["loyalty"]["bonusApplied"] == 50.0
        assert updated.data["cart"]["totals"]["totalPrice"] == 89.0 - 50.0


async def test_mock_coupon_details_eligibility_flag(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        result = await client.call_tool("silpo_get_coupon_details", {"businessCouponId": 520703581})
        assert result.data["canBeAppliedToOrder"] is True
        assert result.data["state"] == "Активний"


async def test_mock_certificates_accept_barcode_objects(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        summary = await client.call_tool("silpo_get_my_shopping_cart", {})
        cart_id = summary.data["cartId"]
        result = await client.call_tool(
            "silpo_add_or_update_certificates",
            {
                "shoppingCartId": cart_id,
                "certificatesToAdd": [{"barcode": "4820000000002", "pincode": "1234"}],
                "certificatesToRemove": [],
            },
        )
        assert result.data["added"][0]["barcode"] == "4820000000002"
        assert result.data["removed"] == []


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


async def test_mock_find_products_batch_skips_empty(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        ctx = {
            "branchId": "bran-1",
            "deliveryType": "DeliveryHome",
            "timeslotStart": "2026-09-06T10:00:00+03:00",
            "timeslotEnd": "2026-09-06T11:00:00+03:00",
        }
        mixed = await client.call_tool(
            "silpo_find_products_batch", {**ctx, "products": ["молоко", "", "   "], "limit": 2}
        )
        assert mixed.data["meta"]["droppedCount"] == 2
        assert mixed.data["meta"]["totalQueries"] == 1
        assert mixed.data["queries"][0]["query"] == "молоко"
        assert "totalFound" in mixed.data["queries"][0]

        all_empty = await client.call_tool("silpo_find_products_batch", {**ctx, "products": ["   "]})
        assert all_empty.data["success"] is True
        assert all_empty.data["queries"] == []
        assert all_empty.data["meta"]["droppedCount"] == 1

        by_article = await client.call_tool("silpo_find_products_batch", {**ctx, "products": ["100001"]})
        assert by_article.data["queries"][0]["totalFound"] == 1
        assert by_article.data["queries"][0]["products"][0]["productId"] == "prd-milk-2pct"


async def test_mock_product_details_has_new_fields(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        result = await client.call_tool(
            "silpo_get_product_details",
            {
                "branchId": "bran-1",
                "slug": "moloko-premiya-25-900-ml",
                "deliveryType": "DeliveryHome",
                "timeslotStart": "2026-09-06T10:00:00+03:00",
                "timeslotEnd": "2026-09-06T11:00:00+03:00",
            },
        )
        assert result.data["displayPrice"] == 36.9
        assert result.data["image"]
        assert result.data["externalProductId"] == 100001
        assert result.data["weighted"] is False


async def test_mock_similar_products_requires_timeslot(mock_server: SilpoMockServer) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        tools = {t.name: t for t in await client.list_tools()}
        required = set(tools["silpo_get_similar_products"].inputSchema.get("required", []))
        assert {"branchId", "slug", "deliveryType", "timeslotStart", "timeslotEnd"} <= required

        result = await client.call_tool(
            "silpo_get_similar_products",
            {
                "branchId": "bran-1",
                "slug": "moloko-premiya-25-900-ml",
                "deliveryType": "DeliveryHome",
                "timeslotStart": "2026-09-06T10:00:00+03:00",
                "timeslotEnd": "2026-09-06T11:00:00+03:00",
                "limit": 2,
            },
        )
        assert len(result.data) == 2
