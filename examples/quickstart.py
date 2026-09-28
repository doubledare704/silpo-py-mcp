#!/usr/bin/env python3
"""Quickstart demo for silpo-py-mcp against the in-memory mock.

Runs a realistic "fill the cart from a shopping list" flow:
find address -> delivery types -> get cart -> search products ->
add to cart -> apply bonuses -> view cart + checkout links.

Run:  uv run examples/quickstart.py
"""

from __future__ import annotations

import asyncio

from silpo_py_mcp import SilpoClient


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
        timeslot_start = "2026-09-06T10:00:00+03:00"
        timeslot_end = "2026-09-06T11:00:00+03:00"
        batch = await client.find_products_batch(
            "bran-1", "DeliveryHome", timeslot_start, timeslot_end, shopping_list, limit=1
        )
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
        if loyalty.can_offer_bonuses:
            print(f"[loyalty] {loyalty.bonus_available:.1f} балабонусів available — applying all.")
            # release-1.111.3: address and shipments are copied from the cart
            # as-is — never hand-built — so read them off update_payloads.
            payloads = updated.cart.update_payloads
            updated = await client.update_shopping_cart(
                cart.cart_id,
                updated.cart.delivery_type,
                payloads.timeslot,
                payloads.address,
                payloads.shipments,
                bonus_requested=loyalty.bonus_available,
            )
            print(f"[cart] after bonuses — total {updated.cart.total_to_pay} UAH")

        # 6. Validate delivery slot and show checkout links
        slots = await client.get_time_slots(updated.cart.branch_id, delivery_types=[updated.cart.delivery_type])
        bookable = [s for s in slots if s.is_bookable]
        print(f"[slots] {len(bookable)}/{len(slots)} bookable; first starts {slots[0].starts_at} (UTC)")
        print(f"[payment] available: {updated.cart.available_payment_types}")
        print(f"[payment] blocked:   {updated.cart.payment.unavailable_types}")
        print(f"[checkout] web:  {updated.cart.checkout_web_link}")
        print(f"[checkout] mobile: {updated.cart.checkout_mobile_link}")

        if updated.cart.validations:
            print(f"[validations] {[v.message for v in updated.cart.validations]}")


if __name__ == "__main__":
    asyncio.run(main())
