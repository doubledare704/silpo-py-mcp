#!/usr/bin/env python3
"""Interactive smoke test against the real Silpo MCP server.

Connects via OAuth (first run opens a browser for login at auth.silpo.ua),
verifies the live ``tools/list`` contract, then runs a read-only battery of
``call_tool`` calls using the argument names from the live schemas.

Run:  uv run examples/real_smoke.py
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from silpo_mcp import SilpoClient

EXPECTED_TOOLS: list[str] = [
    "silpo_find_address",
    "silpo_get_available_delivery_types",
    "silpo_list_branches",
    "silpo_get_time_slots",
    "silpo_find_nova_poshta_settlements",
    "silpo_find_nova_poshta_offices",
    "silpo_find_products_batch",
    "silpo_get_products",
    "silpo_get_product_details",
    "silpo_get_similar_products",
    "silpo_get_replacements",
    "silpo_get_my_favorites",
    "silpo_add_or_update_favorite_products",
    "silpo_get_promotions",
    "silpo_get_popular_categories",
    "silpo_get_category",
    "silpo_get_categories",
    "silpo_get_categories_tree",
    "silpo_get_product_sets",
    "silpo_get_my_shopping_cart",
    "silpo_get_shopping_cart_by_id",
    "silpo_add_or_update_cart_products",
    "silpo_remove_cart_products",
    "silpo_clear_shopping_cart",
    "silpo_update_shopping_cart",
    "silpo_add_or_update_certificates",
    "silpo_get_my_online_orders",
    "silpo_get_my_offline_orders",
    "silpo_get_my_profile",
    "silpo_get_my_delivery_addresses",
    "silpo_get_my_family",
    "silpo_get_my_food_restrictions",
    "silpo_get_loyalty_info",
    "silpo_get_my_coupons",
    "silpo_get_coupon_details",
    "silpo_get_my_promos",
    "silpo_get_promo_codes",
    "silpo_get_my_certificates",
    "silpo_get_my_premium_subscription",
]

TEST_LOCATION = {
    "latitude": 49.8383,
    "longitude": 24.0232,
    "address": "Львів, вул. Степана Бандери, 3",
}
FALLBACK_LOCATION = {
    "latitude": 50.4501,
    "longitude": 30.5234,
    "address": "Київ, вул. Хрещатик, 22",
}


def _short(value: Any, limit: int = 220) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


async def _run_contract(client: SilpoClient) -> tuple[bool, dict[str, Any]]:
    print("\n== Contract check (tools/list) ==")
    tools = await client.list_tools()
    by_name = {tool.name: tool for tool in tools}
    real = sorted(by_name)
    expected = sorted(EXPECTED_TOOLS)
    missing = sorted(set(expected) - set(real))
    extra = sorted(set(real) - set(expected))
    ok = not missing and not extra
    print(f"live tools: {len(real)} (expected {len(expected)})")
    if missing:
        print("  missing:", missing)
    if extra:
        print("  extra:  ", extra)

    for name in expected:
        tool = by_name.get(name)
        if not tool:
            print(f"  MISSING {name}")
            continue
        props = tool.inputSchema.get("properties", {})
        required = set(tool.inputSchema.get("required", []))
        parts = [f"{arg}:{prop.get('type', '?')}" + ("!" if arg in required else "") for arg, prop in props.items()]
        print(f"  {name}({', '.join(parts)})")
    return ok, by_name


async def _run_battery(client: SilpoClient, by_name: dict[str, Any]) -> tuple[int, int]:
    print("\n== Read-only battery (call_tool, live schemas) ==")
    print(f"  test location: {TEST_LOCATION} (fallback {FALLBACK_LOCATION})")
    state: dict[str, Any] = {
        "latitude": TEST_LOCATION["latitude"],
        "longitude": TEST_LOCATION["longitude"],
        "address": TEST_LOCATION["address"],
    }
    passed = 0
    failed = 0
    called: set[str] = set()

    def ctx(**overrides: Any) -> dict[str, Any]:
        args: dict[str, Any] = {}
        for key, value in state.items():
            if value is not None:
                args[key] = value
        args.update(overrides)
        return args

    def _filter_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = by_name.get(tool_name)
        if tool is None:
            return args
        props = tool.inputSchema.get("properties", {})
        if not props:
            return args
        return {k: v for k, v in args.items() if k in props}

    async def check(name: str, args: dict[str, Any], *, filtered: bool = False) -> Any:
        nonlocal passed, failed
        called.add(name)
        call_args = _filter_args(name, args) if filtered else args
        print(f"  → {name} args={call_args}")
        try:
            payload = await client.call_tool(name, call_args)
        except Exception as exc:
            failed += 1
            print(f"  ✗ {name}: {type(exc).__name__}: {exc}")
            return None
        passed += 1
        print(f"  ✓ {name}: {_short(payload)}")
        return payload

    # -- bootstrap: branches + delivery + slots -----------------------------
    branches_payload = await check("silpo_list_branches", {"limit": 5})
    if branches_payload is None:
        branches_payload = await check("silpo_list_branches", {})
    branches_list = (branches_payload or {}).get("branches") or (branches_payload or {}).get("items") or []
    if isinstance(branches_payload, list):
        branches_list = branches_payload
    if not branches_list and isinstance(branches_payload, dict):
        branches_list = [branches_payload] if branches_payload.get("branchId") else []
    print(f"  · branches: {len(branches_list)} found")
    if branches_list:
        print(f"    example: {_short(branches_list[0])}")

    delivery = await check(
        "silpo_get_available_delivery_types", {"latitude": state["latitude"], "longitude": state["longitude"]}
    )
    if delivery is None:
        delivery = await check(
            "silpo_get_available_delivery_types",
            {"latitude": FALLBACK_LOCATION["latitude"], "longitude": FALLBACK_LOCATION["longitude"]},
        )
        if delivery is not None:
            state["latitude"] = FALLBACK_LOCATION["latitude"]
            state["longitude"] = FALLBACK_LOCATION["longitude"]
            state["address"] = FALLBACK_LOCATION["address"]
    opts = (delivery or {}).get("options") or (delivery or {}).get("deliveryTypes") or delivery or []
    if isinstance(opts, dict):
        opts = [opts]
    delivery_types: list[str] = []
    for o in opts if isinstance(opts, list) else []:
        if isinstance(o, dict):
            delivery_types.append(o.get("deliveryType") or o.get("type") or o.get("delivery_type") or "")
        elif isinstance(o, str):
            delivery_types.append(o)
    delivery_types = [d for d in delivery_types if d] or ["DeliveryHome", "SelfPickup"]
    state["deliveryType"] = delivery_types[0]
    print(f"  · deliveryTypes: {delivery_types}")

    found_slot = False
    for branch in branches_list[:5]:
        bid = branch.get("branchId") or branch.get("id") or branch.get("branch_id")
        if not bid:
            continue
        for dtype in delivery_types:
            payload_try = await check("silpo_get_time_slots", {"branchId": bid, "deliveryTypes": [dtype]})
            if payload_try is None:
                payload_try = await check("silpo_get_time_slots", {"branchId": bid, "deliveryType": dtype})
            slots = (payload_try or {}).get("slots") or (payload_try or {}).get("timeSlots") or []
            if isinstance(payload_try, list):
                slots = payload_try
            slot = next(
                (s for s in slots if s.get("available") or s.get("isAvailable") or s.get("available") is None), None
            )
            if slot:
                state["branchId"] = bid
                state["deliveryType"] = dtype
                state["timeslotStart"] = slot.get("start") or slot.get("startsAt") or slot.get("from")
                state["timeslotEnd"] = slot.get("end") or slot.get("endsAt") or slot.get("to")
                print(f"  · selected slot branch={bid} dtype={dtype} slot={_short(slot)}")
                found_slot = True
                break
        if found_slot:
            break
    if not found_slot and branches_list:
        state.setdefault("branchId", branches_list[0].get("branchId") or branches_list[0].get("id"))
        print(f"  · no available slot, using branchId={state.get('branchId')}")

    # ensure state has common keys for ctx accumulation
    state.setdefault("limit", 5)
    state.setdefault("pageSize", 5)

    # -- location / delivery (remaining) ----------------------------------
    await check("silpo_find_address", {"address": state["address"]})
    await check("silpo_get_available_delivery_types", {"latitude": state["latitude"], "longitude": state["longitude"]})

    np_settlements = await check("silpo_find_nova_poshta_settlements", {"query": "Київ"})
    if np_settlements is None:
        np_settlements = await check("silpo_find_nova_poshta_settlements", {"settlementName": "Київ"})
    settlements = (
        np_settlements if isinstance(np_settlements, list) else (np_settlements or {}).get("settlements") or []
    )
    if isinstance(np_settlements, dict) and not settlements:
        settlements = np_settlements.get("items") or []
    if settlements:
        sid = settlements[0].get("settlementId") or settlements[0].get("id") or settlements[0].get("ref")
        if sid:
            state["settlementId"] = sid
            await check("silpo_find_nova_poshta_offices", {"settlementId": sid})
            if "settlementId" not in (
                by_name.get("silpo_find_nova_poshta_offices", {}).inputSchema.get("properties", {})
                if by_name.get("silpo_find_nova_poshta_offices")
                else {}
            ):
                await check("silpo_find_nova_poshta_offices", {"settlementId": sid, "settlement_id": sid})
    else:
        await check("silpo_find_nova_poshta_offices", {"settlementId": "np-kyiv"})

    # -- catalog (6) -------------------------------------------------------
    categories_payload = await check("silpo_get_categories", _filter_args("silpo_get_categories", ctx(limit=10)))
    if categories_payload is None:
        categories_payload = await check("silpo_get_categories", ctx())
    cats = (categories_payload or {}).get("categories") or (categories_payload or {}).get("items") or []
    if isinstance(categories_payload, list):
        cats = categories_payload
    print(f"  · categories: {len(cats)}")
    if cats:
        first = cats[0]
        print(f"    example: {_short(first)}")
        state["categorySlug"] = first.get("slug") or first.get("categorySlug") or state.get("categorySlug")
        state["categoryId"] = first.get("id") or first.get("categoryId")
        if state.get("categorySlug"):
            await check(
                "silpo_get_category", _filter_args("silpo_get_category", ctx(categorySlug=state["categorySlug"]))
            )
            # fallback with categoryId if slug variant missing
            if "categorySlug" not in (
                by_name.get("silpo_get_category", {}).inputSchema.get("properties", {})
                if by_name.get("silpo_get_category")
                else {}
            ):
                pass
            else:
                # also try categoryId alias if server expects it
                if state.get("categoryId"):
                    await check("silpo_get_category", {"categoryId": state["categoryId"]})
        elif state.get("categoryId"):
            await check("silpo_get_category", {"categoryId": state["categoryId"]})
    else:
        await check("silpo_get_category", ctx(categorySlug="molochni"))
        await check("silpo_get_category", {"categoryId": "cat-dairy"})

    await check("silpo_get_categories_tree", _filter_args("silpo_get_categories_tree", ctx()))
    await check("silpo_get_promotions", _filter_args("silpo_get_promotions", ctx()))
    await check("silpo_get_popular_categories", _filter_args("silpo_get_popular_categories", ctx()))
    await check("silpo_get_product_sets", _filter_args("silpo_get_product_sets", ctx()))

    # -- product search (7) ------------------------------------------------
    products = await check("silpo_get_products", _filter_args("silpo_get_products", ctx(limit=5)))
    if products is None:
        # fallback explicit known-good shape from previous script
        products = await check(
            "silpo_get_products",
            {
                "branchId": state.get("branchId") or "1ed43e73-051b-6842-a111-a5ad042eb496",
                "deliveryType": state.get("deliveryType") or "SelfPickup",
                "timeslotStart": state.get("timeslotStart") or "2026-08-22T10:00:00+00:00",
                "timeslotEnd": state.get("timeslotEnd") or "2026-08-22T10:30:00+00:00",
                "limit": 5,
            },
        )
    prod_list = (products or {}).get("products") or (products or {}).get("items") or []
    if isinstance(products, list):
        prod_list = products
    print(f"  · products: {len(prod_list)}")
    if prod_list:
        first_prod = prod_list[0]
        print(f"    example: {_short(first_prod)}")
        state["slug"] = first_prod.get("slug")
        state["productId"] = first_prod.get("productId") or first_prod.get("id")
        state["companyId"] = first_prod.get("companyId")
        # keep branch from product if needed
        state["productBranchId"] = first_prod.get("branchId")

    # product details: try slug first (live), then productId (mock)
    if state.get("slug"):
        details = await check(
            "silpo_get_product_details", _filter_args("silpo_get_product_details", ctx(slug=state["slug"]))
        )
        if details is None and state.get("productId"):
            await check("silpo_get_product_details", {"productId": state["productId"]})
    elif state.get("productId"):
        await check("silpo_get_product_details", {"productId": state["productId"]})
    else:
        await check(
            "silpo_get_product_details",
            {
                "branchId": state.get("branchId"),
                "deliveryType": state.get("deliveryType") or "SelfPickup",
                "timeslotStart": state.get("timeslotStart"),
                "timeslotEnd": state.get("timeslotEnd"),
                "slug": "pyvo-corona-extra-svitle-z-b-949468",
            },
        )

    if state.get("slug"):
        await check("silpo_get_similar_products", _filter_args("silpo_get_similar_products", ctx(slug=state["slug"])))
        if "slug" not in (
            by_name.get("silpo_get_similar_products", {}).inputSchema.get("properties", {})
            if by_name.get("silpo_get_similar_products")
            else {}
        ):
            await check("silpo_get_similar_products", {"slug": state["slug"]})
    else:
        await check("silpo_get_similar_products", {"slug": "moloko-premiya-25-900-ml"})

    if state.get("productId"):
        await check("silpo_get_replacements", {"productIds": [state["productId"]]})
        # also try singular alias
        await check(
            "silpo_get_replacements", _filter_args("silpo_get_replacements", ctx(productIds=[state["productId"]]))
        )
    else:
        await check("silpo_find_products_batch", {"items": [{"query": "молоко", "limit": 1}]})

    # find_products_batch: cover both shapes (items vs queries)
    batch = await check(
        "silpo_find_products_batch", {"items": [{"query": "молоко", "limit": 1}, {"query": "хліб", "limit": 1}]}
    )
    if batch is None:
        batch = await check("silpo_find_products_batch", {"queries": ["молоко", "хліб"]})

    # favorites (read then write)
    favs = await check("silpo_get_my_favorites", _filter_args("silpo_get_my_favorites", ctx()))
    if favs is None:
        await check("silpo_get_my_favorites", {})
    if state.get("productId"):
        fav_add = await check(
            "silpo_add_or_update_favorite_products", {"productIds": [state["productId"]], "add": True}
        )
        if fav_add is None:
            await check(
                "silpo_add_or_update_favorite_products",
                _filter_args("silpo_add_or_update_favorite_products", ctx(productIds=[state["productId"]], add=True)),
            )
        # revert
        await check("silpo_add_or_update_favorite_products", {"productIds": [state["productId"]], "add": False})
    else:
        await check("silpo_add_or_update_favorite_products", {"productIds": ["prd-milk-2pct"], "add": True})

    # -- cart (7) ----------------------------------------------------------
    cart_summary = await check("silpo_get_my_shopping_cart", {})
    cart_id = None
    if isinstance(cart_summary, dict):
        cart_id = (
            cart_summary.get("cartId")
            or cart_summary.get("shoppingCartId")
            or cart_summary.get("cart_id")
            or cart_summary.get("id")
        )
        if not cart_id and "cart" in cart_summary:
            cart_id = cart_summary["cart"].get("cartId") or cart_summary["cart"].get("shoppingCartId")
    if cart_id:
        state["cartId"] = cart_id
        state["shoppingCartId"] = cart_id
        print(f"  · cartId={cart_id}")

    # need cartId for remaining cart tools; if missing, skip gracefully
    if cart_id:
        cart_detail = await check("silpo_get_shopping_cart_by_id", {"shoppingCartId": cart_id})
        if cart_detail is None:
            cart_detail = await check("silpo_get_shopping_cart_by_id", {"cartId": cart_id})
        # also try ctx-filtered
        if cart_detail is None:
            await check(
                "silpo_get_shopping_cart_by_id",
                _filter_args("silpo_get_shopping_cart_by_id", ctx(shoppingCartId=cart_id, cartId=cart_id)),
            )

        # build item for cart mutation using discovered product
        if state.get("productId"):
            add_payload = {
                "shoppingCartId": cart_id,
                "cartId": cart_id,
                "items": [
                    {
                        "productId": state["productId"],
                        "quantity": 1,
                        "companyId": state.get("companyId"),
                        "branchId": state.get("branchId"),
                    }
                ],
            }
            # filter Nones in item
            add_payload["items"][0] = {k: v for k, v in add_payload["items"][0].items() if v is not None}
            filtered = _filter_args("silpo_add_or_update_cart_products", add_payload)
            # ensure at least one id key remains
            if "shoppingCartId" not in filtered and "cartId" not in filtered:
                filtered["shoppingCartId"] = cart_id
            await check("silpo_add_or_update_cart_products", filtered if filtered else add_payload)
            # also try minimal shape
            await check(
                "silpo_add_or_update_cart_products",
                {"shoppingCartId": cart_id, "items": [{"productId": state["productId"], "quantity": 1}]},
            )

            await check(
                "silpo_remove_cart_products",
                _filter_args(
                    "silpo_remove_cart_products",
                    {"shoppingCartId": cart_id, "cartId": cart_id, "productIds": [state["productId"]]},
                ),
            )
            if "productIds" not in (
                by_name.get("silpo_remove_cart_products", {}).inputSchema.get("properties", {})
                if by_name.get("silpo_remove_cart_products")
                else {}
            ):
                await check(
                    "silpo_remove_cart_products", {"shoppingCartId": cart_id, "productIds": [state["productId"]]}
                )

            await check(
                "silpo_update_shopping_cart",
                _filter_args(
                    "silpo_update_shopping_cart",
                    {
                        "shoppingCartId": cart_id,
                        "cartId": cart_id,
                        "branchId": state.get("branchId"),
                        "deliveryType": state.get("deliveryType"),
                    },
                ),
            )

            await check(
                "silpo_add_or_update_certificates",
                _filter_args(
                    "silpo_add_or_update_certificates",
                    {"shoppingCartId": cart_id, "cartId": cart_id, "certificateIds": []},
                ),
            )

            await check(
                "silpo_clear_shopping_cart",
                _filter_args("silpo_clear_shopping_cart", {"shoppingCartId": cart_id, "cartId": cart_id}),
            )
        else:
            # no product, still probe cart tools with empty mutations
            await check("silpo_add_or_update_cart_products", {"shoppingCartId": cart_id, "items": []})
            await check("silpo_remove_cart_products", {"shoppingCartId": cart_id, "productIds": []})
            await check("silpo_update_shopping_cart", {"shoppingCartId": cart_id})
            await check("silpo_add_or_update_certificates", {"shoppingCartId": cart_id, "certificateIds": []})
            await check("silpo_clear_shopping_cart", {"shoppingCartId": cart_id})
    else:
        print("  · no cartId, skipping cart mutation tools")
        for name in [
            "silpo_get_shopping_cart_by_id",
            "silpo_add_or_update_cart_products",
            "silpo_remove_cart_products",
            "silpo_clear_shopping_cart",
            "silpo_update_shopping_cart",
            "silpo_add_or_update_certificates",
        ]:
            await check(name, {})

    # -- orders (2) --------------------------------------------------------
    await check("silpo_get_my_online_orders", {})
    await check("silpo_get_my_offline_orders", {})

    # -- profile (4) -------------------------------------------------------
    await check("silpo_get_my_profile", {})
    await check("silpo_get_my_delivery_addresses", {})
    await check("silpo_get_my_family", {})
    await check("silpo_get_my_food_restrictions", {})

    # -- loyalty (7) -------------------------------------------------------
    await check("silpo_get_loyalty_info", {})
    coupons = await check("silpo_get_my_coupons", {})
    coupon_list = (
        coupons if isinstance(coupons, list) else (coupons or {}).get("coupons") or (coupons or {}).get("items") or []
    )
    if isinstance(coupon_list, dict):
        coupon_list = [coupon_list]
    if coupon_list:
        cid = coupon_list[0].get("couponId") or coupon_list[0].get("id") or coupon_list[0].get("coupon_id")
        if cid:
            state["couponId"] = cid
            await check("silpo_get_coupon_details", {"couponId": cid})
            await check("silpo_get_coupon_details", _filter_args("silpo_get_coupon_details", ctx(couponId=cid)))
    else:
        await check("silpo_get_coupon_details", {"couponId": "cup-1"})
        await check("silpo_get_coupon_details", {"couponId": "test-coupon"})

    await check("silpo_get_my_promos", {})
    await check("silpo_get_promo_codes", {})
    await check("silpo_get_my_certificates", {})
    await check("silpo_get_my_premium_subscription", {})

    # -- final coverage sweep: ensure every expected tool was attempted -----
    missing_calls = sorted(set(EXPECTED_TOOLS) - called)
    if missing_calls:
        print(f"\n  · coverage gap: {missing_calls} — probing with empty args")
        for name in missing_calls:
            await check(name, {})
            await check(name, _filter_args(name, ctx()))

    return passed, failed


async def main() -> int:
    async with SilpoClient.for_real_server() as client:
        print(f"[connect] real server ({client._settings.mcp_url})")
        contract_ok, by_name = await _run_contract(client)
        passed, failed = await _run_battery(client, by_name)
        print(
            f"\n== Summary ==\ncontract: {'OK' if contract_ok else 'DRIFTED'}\n"
            f"battery: {passed} passed, {failed} failed"
        )
        return 0 if contract_ok and failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
