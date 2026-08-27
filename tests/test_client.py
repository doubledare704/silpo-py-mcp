"""Tests for the high-level SilpoClient against the in-memory mock."""

from __future__ import annotations

from silpo_mcp import SilpoClient
from silpo_mcp.models import (
    Address,
    BatchProductResult,
    CartUpdateResult,
    Category,
    Coupon,
    LoyaltyInfo,
    ProductSearchResult,
    SilpoCart,
    SilpoProduct,
    TimeSlot,
)


async def test_list_tools(client: SilpoClient) -> None:
    tools = await client.list_tools()
    assert len(tools) == 39
    assert all(tool.name.startswith("silpo_") for tool in tools)


async def test_location_group(client: SilpoClient) -> None:
    address: Address = await client.find_address("Київ, вул. Анни Ахматової, 9")
    assert address.coordinates.lat == 50.3957

    delivery = await client.get_available_delivery_types(50.0, 30.0)
    assert len(delivery) == 2

    branches = await client.list_branches(has_pickup=True)
    assert len(branches) == 2

    slots: list[TimeSlot] = await client.get_time_slots("bran-1", "DeliveryHome")
    assert len(slots) == 3
    assert slots[0].is_express

    settlements = await client.find_nova_poshta_settlements("Київ")
    assert settlements[0].name == "Київ"

    offices = await client.find_nova_poshta_offices("np-kyiv")
    assert len(offices) == 2


async def test_product_search_group(client: SilpoClient) -> None:
    result: ProductSearchResult = await client.get_products(query="молоко")
    assert result.total == 1
    assert isinstance(result.items[0], SilpoProduct)
    assert result.items[0].is_private_label

    batch: BatchProductResult = await client.find_products_batch(["молоко", "сир", "nonexistent"])
    assert "молоко" in batch.results
    assert "nonexistent" in batch.unmatched

    details = await client.get_product_details("prd-milk-2pct")
    assert details.composition

    similar = await client.get_similar_products("moloko-premiya-25-900-ml")
    assert len(similar) == 2

    await client.update_favorites(["prd-bread"], add=True)
    favorites = await client.get_favorites()
    assert [p.product_id for p in favorites] == ["prd-bread"]


async def test_catalog_group(client: SilpoClient) -> None:
    promotions = await client.get_promotions()
    assert len(promotions) == 2

    categories: list[Category] = await client.get_categories()
    assert len(categories) == 4

    tree = await client.get_categories_tree()
    assert len(tree.root_categories) == 3

    popular = await client.get_popular_categories()
    assert len(popular) == 3

    sets = await client.get_product_sets()
    assert sets[0].title == "Сніданок за 150 грн"


async def test_full_cart_workflow(client: SilpoClient) -> None:
    cart = await client.get_cart()
    cart_id = cart.cart_id

    added: CartUpdateResult = await client.add_or_update_cart_products(
        cart_id,
        [
            {
                "productId": "prd-milk-2pct",
                "companyId": "co-1",
                "branchId": "bran-1",
                "quantity": 2,
            },
            {"productId": "prd-bread", "companyId": "co-2", "branchId": "bran-1", "quantity": 1},
        ],
    )
    assert added.cart.totals.items_price == 2 * 36.9 + 28.5

    fetched: SilpoCart = await client.get_cart_by_id(cart_id)
    assert len(fetched.items) == 2
    assert fetched.checkout_web_link

    updated = await client.update_shopping_cart(
        cart_id, bonus_requested=25.0, timeslot="slot-1", address="Київ, вул. Центральна"
    )
    assert updated.cart.loyalty.bonus_applied == 25.0
    assert updated.cart.address == "Київ, вул. Центральна"

    removed = await client.remove_cart_products(cart_id, ["prd-bread"])
    assert len(removed.cart.items) == 1

    cleared = await client.clear_cart(cart_id)
    assert cleared.cart.items == []


async def test_orders_profile_loyalty_groups(client: SilpoClient) -> None:
    online = await client.get_online_orders()
    assert online[0].status == "delivered"

    offline = await client.get_offline_orders()
    assert offline[0].branch_name

    profile = await client.get_profile()
    assert profile.name

    addresses = await client.get_delivery_addresses()
    assert addresses[0].address_id

    family = await client.get_family()
    assert family[0].member_type == "child"

    restrictions = await client.get_food_restrictions()
    assert "безлактозна дієта" in restrictions.restrictions

    loyalty: LoyaltyInfo = await client.get_loyalty_info()
    assert loyalty.bonus_balance == 125.5

    coupons: list[Coupon] = await client.get_coupons()
    assert coupons[0].barcode

    coupon = await client.get_coupon_details("cup-1")
    assert coupon.conditions

    promos = await client.get_promos()
    assert promos[0].promo_id

    promo_codes = await client.get_promo_codes()
    assert promo_codes[0].code == "SUMMER2026"

    certificates = await client.get_certificates()
    assert certificates[0].nominal == 200.0

    premium = await client.get_premium_subscription()
    assert premium.is_active
