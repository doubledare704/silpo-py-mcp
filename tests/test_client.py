"""Tests for the high-level SilpoClient against the in-memory mock."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from silpo_py_mcp import SilpoClient
from silpo_py_mcp.models import (
    Address,
    BatchProductResult,
    CartSummary,
    CartUpdateResult,
    Category,
    Coupon,
    CreateShoppingCartResult,
    LoyaltyInfo,
    ProductSearchResult,
    SilpoCart,
    SilpoProduct,
    TimeSlot,
)

TS = "2026-09-06T10:00:00+03:00"
TE = "2026-09-06T11:00:00+03:00"


async def test_list_tools(client: SilpoClient) -> None:
    tools = await client.list_tools()
    assert len(tools) == 40
    assert all(tool.name.startswith("silpo_") for tool in tools)


async def test_location_group(client: SilpoClient) -> None:
    address: Address = await client.find_address("Київ, вул. Анни Ахматової, 9")
    assert address.coordinates is not None
    assert address.coordinates.lat == 50.3957

    delivery = await client.get_available_delivery_types(50.0, 30.0)
    assert len(delivery) == 2

    branches = await client.list_branches(has_pickup=True)
    assert len(branches) == 2

    slots: list[TimeSlot] = await client.get_time_slots("bran-1", delivery_types=["DeliveryHome"])
    assert len(slots) == 3
    assert slots[0].is_express

    settlements = await client.find_nova_poshta_settlements("Київ")
    assert settlements[0].name == "Київ"

    offices = await client.find_nova_poshta_offices("np-kyiv")
    assert len(offices) == 2


async def test_product_search_group(client: SilpoClient) -> None:
    result: ProductSearchResult = await client.get_products(
        "bran-1", "DeliveryHome", TS, TE, category="Молочні продукти"
    )
    assert result.total == 2
    assert isinstance(result.items[0], SilpoProduct)
    assert result.items[0].is_private_label

    batch: BatchProductResult = await client.find_products_batch(
        "bran-1", "DeliveryHome", TS, TE, ["молоко", "сир", "nonexistent"]
    )
    assert "молоко" in batch.results
    assert "nonexistent" in batch.unmatched
    assert batch.dropped_count == 0

    details = await client.get_product_details("bran-1", "moloko-premiya-25-900-ml", "DeliveryHome", TS, TE)
    assert details.url
    assert details.attributes
    assert details.display_price == 36.9
    assert details.image
    assert details.external_product_id == 100001

    similar = await client.get_similar_products("bran-1", "moloko-premiya-25-900-ml", "DeliveryHome", TS, TE)
    assert len(similar) == 2
    assert similar[0].display_price is not None

    await client.update_favorites([{"productId": "prd-bread", "externalProductId": 0, "toDelete": False}])
    favorites = await client.get_favorites("bran-1", "DeliveryHome", TS)
    assert [p.product_id for p in favorites] == ["prd-bread"]


async def test_catalog_group(client: SilpoClient) -> None:
    promotions = await client.get_promotions("bran-1", "DeliveryHome", TS, TE)
    assert len(promotions) == 2

    categories: list[Category] = await client.get_categories("bran-1")
    assert len(categories) == 4

    tree = await client.get_categories_tree("bran-1", "DeliveryHome", TS, TE)
    assert len(tree.root_categories) == 3

    popular = await client.get_popular_categories("bran-1", "DeliveryHome")
    assert len(popular) == 3

    sets = await client.get_product_sets("bran-1")
    assert sets[0].title == "Сніданок за 150 грн"


async def test_cart_mutation_wire_args(client: SilpoClient) -> None:
    """Cart mutations must send the live payload keys (shoppingCartId + products / certificatesTo*)."""

    captured: list[tuple[str, dict[str, Any]]] = []
    real_call_tool = client.call_tool

    async def spy(name: str, arguments: Mapping[str, Any]) -> Any:
        captured.append((str(name), dict(arguments)))
        return await real_call_tool(name, arguments)

    client.call_tool = spy  # type: ignore[method-assign]

    cart = await client.get_cart()
    cart_id = cart.resolved_cart_id
    assert cart_id is not None

    await client.add_or_update_cart_products(cart_id, [{"productId": "prd-milk-2pct", "quantity": 2}])
    await client.remove_cart_products(cart_id, ["prd-milk-2pct"])
    await client.add_or_update_certificates(cart_id, ["cert-1"])

    by_name = {name: args for name, args in captured}
    assert by_name["silpo_add_or_update_cart_products"] == {
        "shoppingCartId": cart_id,
        "products": [{"productId": "prd-milk-2pct", "quantity": 2}],
    }
    assert by_name["silpo_remove_cart_products"] == {
        "shoppingCartId": cart_id,
        "products": [{"productId": "prd-milk-2pct"}],
    }
    assert by_name["silpo_add_or_update_certificates"] == {
        "shoppingCartId": cart_id,
        "certificatesToAdd": [{"barcode": "cert-1"}],
        "certificatesToRemove": [],
    }


async def test_full_cart_workflow(client: SilpoClient) -> None:
    cart = await client.get_cart()
    cart_id = cart.resolved_cart_id
    assert cart_id is not None

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
        cart_id,
        "DeliveryHome",
        {"start": TS, "end": TE},
        {"address": "Київ, вул. Центральна"},
        [
            {
                "branchId": "bran-1",
                "companyId": "co-1",
                "deliveryType": "DeliveryHome",
                "timeslot": {"start": TS, "end": TE},
            }
        ],
        bonus_requested=25.0,
    )
    assert updated.cart.loyalty.bonus_applied == 25.0
    assert updated.cart.address == {"address": "Київ, вул. Центральна"}

    removed = await client.remove_cart_products(cart_id, ["prd-bread"])
    assert len(removed.cart.items) == 1

    cleared = await client.clear_cart(cart_id)
    assert cleared.cart.items == []


async def test_create_shopping_cart(client: SilpoClient) -> None:
    created: CreateShoppingCartResult = await client.create_shopping_cart(
        address_type="house",
        latitude=50.3957,
        longitude=30.6217,
        delivery_type="DeliveryHome",
        branch_id="bran-1",
        timeslot_start="2026-09-06T10:00:00+03:00",
        timeslot_end="2026-09-06T11:00:00+03:00",
        city="Київ",
        street="вул. Анни Ахматової",
        house="9",
    )
    assert created.success is True
    assert created.shopping_cart_id

    again = await client.create_shopping_cart(
        address_type="house",
        latitude=50.3957,
        longitude=30.6217,
        delivery_type="DeliveryHome",
        branch_id="bran-1",
        timeslot_start="2026-09-06T10:00:00+03:00",
        timeslot_end="2026-09-06T11:00:00+03:00",
    )
    assert again.shopping_cart_id == created.shopping_cart_id

    summary: CartSummary = await client.get_cart()
    assert summary.resolved_cart_id == created.shopping_cart_id

    fetched: SilpoCart = await client.get_cart_by_id(created.shopping_cart_id)
    assert fetched.branch_id == "bran-1"
    assert fetched.delivery_type == "DeliveryHome"


async def test_cart_summary_exists_false() -> None:
    summary = CartSummary.model_validate({"exists": False})
    assert summary.exists is False
    assert summary.resolved_cart_id is None


async def test_orders_profile_loyalty_groups(client: SilpoClient) -> None:
    online = await client.get_online_orders()
    assert online[0].status == "delivered"

    offline = await client.get_offline_orders("bran-1", "DeliveryHome", TS, TE)
    assert offline[0].branch_name

    profile = await client.get_profile()
    assert profile.name

    addresses = await client.get_delivery_addresses()
    assert addresses[0].address_id

    family = await client.get_family()
    assert family[0].name == "Софія"
    assert any(member.its_me for member in family)

    restrictions = await client.get_food_restrictions()
    assert "lactose-free" in restrictions.restrictions

    loyalty: LoyaltyInfo = await client.get_loyalty_info()
    assert loyalty.bonus_balance == 125.5

    coupons: list[Coupon] = await client.get_coupons()
    assert coupons[0].reward_value == 50.0

    coupon = await client.get_coupon_details(520703581)
    assert coupon.can_be_applied_to_order is True
    assert coupon.business_coupon_id == 520703581
    assert coupon.state == "Активний"

    promos = await client.get_promos()
    assert promos[0].promo_id

    promo_codes = await client.get_promo_codes()
    assert promo_codes[0].code == "SUMMER2026"

    certificates = await client.get_certificates()
    assert certificates[0].total_price == 200.0

    premium = await client.get_premium_subscription()
    assert premium.status == "active"
    assert premium.web_link


async def test_certificates_accept_barcode_dicts(client: SilpoClient) -> None:
    cart = await client.get_cart()
    cart_id = cart.resolved_cart_id
    assert cart_id is not None

    result = await client.add_or_update_certificates(cart_id, [{"barcode": "4820000000002", "pincode": "1234"}])
    assert result.added == [{"barcode": "4820000000002", "faceValue": None, "validations": []}]
    assert result.removed == []


async def test_category_children_map_to_subcategories(client: SilpoClient) -> None:
    detail = await client.get_category("bran-1", "DeliveryHome", "molochni")
    assert detail.category.slug == "molochni"
    assert [c.slug for c in detail.subcategories] == ["yaytsya"]


async def test_online_order_live_shape(client: SilpoClient) -> None:
    online = await client.get_online_orders()
    assert online[0].total_price == 245.5
    assert online[0].items[0].title == "Молоко Премія 2.5% 900 мл"


async def test_find_products_batch_skips_empty_entries(client: SilpoClient) -> None:
    batch = await client.find_products_batch("bran-1", "DeliveryHome", TS, TE, ["молоко", "", "   ", "хліб"])
    assert batch.dropped_count == 2
    assert "молоко" in batch.results or "хліб" in batch.results

    empty = await client.find_products_batch("bran-1", "DeliveryHome", TS, TE, ["   "])
    assert empty.results == {}
    assert empty.unmatched == []
    assert empty.dropped_count == 1


async def test_get_products_price_filters_use_display_price(client: SilpoClient) -> None:
    result = await client.get_products(
        "bran-1", "DeliveryHome", TS, TE, category="Молочні продукти", from_price=30.0, to_price=40.0
    )
    assert result.total == 1
    assert result.items[0].product_id == "prd-milk-2pct"
    assert result.items[0].display_price == 36.9

    wide = await client.get_products("bran-1", "DeliveryHome", TS, TE, category="Молочні продукти")
    assert all(item.display_price is not None for item in wide.items)
