"""Tests for the Silpo mock server: tool inventory and behavior."""

from __future__ import annotations

from fastmcp import Client

# Exact 39 tool names from the official Silpo docs (https://ai-factory.silpo.ua/docs/mcp).
EXPECTED_TOOLS: list[str] = [
    # Location & delivery (6)
    "silpo_find_address",
    "silpo_get_available_delivery_types",
    "silpo_list_branches",
    "silpo_get_time_slots",
    "silpo_find_nova_poshta_settlements",
    "silpo_find_nova_poshta_offices",
    # Product search (7)
    "silpo_find_products_batch",
    "silpo_get_products",
    "silpo_get_product_details",
    "silpo_get_similar_products",
    "silpo_get_replacements",
    "silpo_get_my_favorites",
    "silpo_add_or_update_favorite_products",
    # Catalog (6)
    "silpo_get_promotions",
    "silpo_get_popular_categories",
    "silpo_get_category",
    "silpo_get_categories",
    "silpo_get_categories_tree",
    "silpo_get_product_sets",
    # Cart (7)
    "silpo_get_my_shopping_cart",
    "silpo_get_shopping_cart_by_id",
    "silpo_add_or_update_cart_products",
    "silpo_remove_cart_products",
    "silpo_clear_shopping_cart",
    "silpo_update_shopping_cart",
    "silpo_add_or_update_certificates",
    # Orders (2)
    "silpo_get_my_online_orders",
    "silpo_get_my_offline_orders",
    # Profile (4)
    "silpo_get_my_profile",
    "silpo_get_my_delivery_addresses",
    "silpo_get_my_family",
    "silpo_get_my_food_restrictions",
    # Loyalty & promotions (7)
    "silpo_get_loyalty_info",
    "silpo_get_my_coupons",
    "silpo_get_coupon_details",
    "silpo_get_my_promos",
    "silpo_get_promo_codes",
    "silpo_get_my_certificates",
    "silpo_get_my_premium_subscription",
]


async def test_mock_exposes_all_39_documented_tools(mock_server: object) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        names = sorted(tool.name for tool in await client.list_tools())
    assert len(names) == 39
    assert names == sorted(EXPECTED_TOOLS)


async def test_mock_get_products_filters(mock_server: object) -> None:
    client = Client(mock_server.fastmcp)  # type: ignore[attr-defined]
    async with client:
        result = await client.call_tool("silpo_get_products", {"query": "молоко"})
        assert result.data["total"] == 1
        assert result.data["items"][0]["productId"] == "prd-milk-2pct"

        on_sale = await client.call_tool("silpo_get_products", {"onSale": True})
        assert on_sale.data["total"] == 2


async def test_mock_cart_lifecycle(mock_server: object) -> None:
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


async def test_mock_apply_bonuses(mock_server: object) -> None:
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
