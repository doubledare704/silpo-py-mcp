#!/usr/bin/env python3
"""Quickstart demo for silpo-mcp against the in-memory mock.

Runs a realistic "fill the cart from a shopping list" flow:
find address -> delivery types -> get cart -> search products ->
add to cart -> apply bonuses -> view cart + checkout links.

Run:  uv run examples/quickstart.py
"""

from __future__ import annotations

import asyncio

from silpo_mcp import SilpoClient


async def main() -> None:
    async with SilpoClient.for_mock() as client:
        tools = await client.list_tools()
        print(f"[tools] {len(tools)} silpo_* tools available\n")

        # 1. Locate the guest
        address = await client.find_address("Київ, вул. Анни Ахматової, 9")
        print(f"[address] {address.text} ({address.coordinates.lat}, {address.coordinates.lng})")

        delivery = await client.get_available_delivery_types(address.coordinates.lat, address.coordinates.lng)
        print(f"[delivery] {[d.type.value for d in delivery]}")

        # 2. Get the active cart
        cart = await client.get_cart()
        print(f"[cart] active cart: {cart.cart_id}")

        # 3. Search products from a shopping list
        shopping_list = ["молоко", "хліб", "яйця"]
        batch = await client.find_products_batch(shopping_list, limit=1)
        print(f"[search] matched: {list(batch.results.keys())}; unmatched: {batch.unmatched}")

        items = []
        for _query, matches in batch.results.items():
            for product in matches:
                items.append(
                    {
                        "productId": product.product_id,
                        "companyId": product.company_id,
                        "branchId": product.branch_id,
                        "quantity": 1,
                    }
                )

        # 4. Fill the cart
        updated = await client.add_or_update_cart_products(cart.cart_id, items)
        filled = f"{len(updated.cart.items)} items — total {updated.cart.totals.total_price} UAH"
        print(f"[cart] filled with {filled}")

        # 5. Offer/apply bonuses (documented workflow)
        loyalty = updated.cart.loyalty
        if loyalty.bonus_available > 0 and loyalty.bonus_requested is None:
            print(f"[loyalty] {loyalty.bonus_available:.1f} балабонусів available — applying all.")
            updated = await client.update_shopping_cart(cart.cart_id, bonus_requested=loyalty.bonus_available)
            print(f"[cart] after bonuses — total {updated.cart.totals.total_price} UAH")

        # 6. Validate delivery slot and show checkout links
        slots = await client.get_time_slots(updated.cart.branch_id, updated.cart.delivery_type)
        print(f"[slots] {len(slots)} available; first starts {slots[0].starts_at}")
        print(f"[checkout] web:  {updated.cart.checkout_web_link}")
        print(f"[checkout] mobile: {updated.cart.checkout_mobile_link}")

        if updated.cart.validations:
            print(f"[validations] {[v.message for v in updated.cart.validations]}")


if __name__ == "__main__":
    asyncio.run(main())
