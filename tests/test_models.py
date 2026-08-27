"""Tests for Pydantic model validation against realistic payloads."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from silpo_mcp.models import (
    SilpoCart,
    SilpoProduct,
    TimeSlot,
)


def test_product_alias_parsing() -> None:
    raw = {
        "productId": "p1",
        "companyId": "c1",
        "branchId": "b1",
        "title": "Молоко",
        "price": 36.9,
        "oldPrice": 45.0,
        "isOnSale": True,
        "isPrivateLabel": True,
        "imageUrl": "https://example.com/milk.png",
    }
    product = SilpoProduct.model_validate(raw)
    assert product.product_id == "p1"
    assert product.old_price == 45.0
    assert product.is_on_sale
    assert product.image_url == "https://example.com/milk.png"


def test_product_accepts_field_names_too() -> None:
    product = SilpoProduct(
        product_id="p1",
        company_id="c1",
        branch_id="b1",
        title="Хліб",
        price=28.5,
    )
    assert product.title == "Хліб"
    assert product.is_available  # default


def test_product_requires_required_fields() -> None:
    with pytest.raises(ValidationError):
        SilpoProduct.model_validate({"title": "no ids"})


def test_cart_alias_parsing() -> None:
    raw = {
        "cartId": "cart-1",
        "branchId": "bran-1",
        "deliveryType": "DeliveryHome",
        "items": [
            {
                "productId": "p1",
                "companyId": "c1",
                "branchId": "b1",
                "title": "Молоко",
                "quantity": 2,
                "unitPrice": 36.9,
                "totalPrice": 73.8,
            }
        ],
        "totals": {"totalPrice": 73.8, "itemsPrice": 73.8, "deliveryPrice": 0.0},
        "loyalty": {"isEnabled": True, "bonusAvailable": 125.5},
        "checkoutWebLink": "https://silpo.ua/cart/cart-1",
        "checkoutMobileLink": "silpo://cart/cart-1",
    }
    cart = SilpoCart.model_validate(raw)
    assert cart.cart_id == "cart-1"
    assert cart.totals.total_price == 73.8
    assert cart.loyalty.bonus_available == 125.5
    assert cart.checkout_web_link
    assert len(cart.items) == 1


def test_time_slot_alias_parsing() -> None:
    slot = TimeSlot.model_validate(
        {
            "id": "s1",
            "deliveryType": "DeliveryHome",
            "branchId": "b1",
            "startsAt": "2026-09-02T08:00:00Z",
            "endsAt": "2026-09-02T10:00:00Z",
            "price": 0.0,
            "isExpress": True,
        }
    )
    assert slot.delivery_type == "DeliveryHome"
    assert slot.is_express


def test_cart_defaults() -> None:
    cart = SilpoCart(
        cart_id="cart-1",
        branch_id="b1",
        delivery_type="DeliveryHome",
        totals={"totalPrice": 0.0, "itemsPrice": 0.0},
    )
    assert cart.validations == []
    assert cart.items == []
