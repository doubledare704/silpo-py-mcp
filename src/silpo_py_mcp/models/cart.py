"""Cart and checkout models."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from silpo_py_mcp.models.base import SilpoModel


class CartItem(SilpoModel):
    """A single product line in the cart."""

    product_id: str = Field(alias="productId")
    company_id: str = Field(alias="companyId")
    branch_id: str = Field(alias="branchId")
    title: str
    quantity: float
    unit_price: float = Field(alias="unitPrice")
    total_price: float = Field(alias="totalPrice")
    is_available: bool = Field(default=True, alias="isAvailable")


class CartTotals(SilpoModel):
    """Monetary totals of the cart."""

    total_price: float = Field(alias="totalPrice")
    items_price: float = Field(alias="itemsPrice")
    delivery_price: float = Field(default=0.0, alias="deliveryPrice")
    discount: float = Field(default=0.0)
    bonuses_to_apply: float = Field(default=0.0, alias="bonusesToApply")


class CartLoyalty(SilpoModel):
    """Loyalty state attached to the cart."""

    is_enabled: bool = Field(default=False, alias="isEnabled")
    bonus_available: float = Field(default=0.0, alias="bonusAvailable")
    bonus_requested: float | None = Field(default=None, alias="bonusRequested")
    bonus_applied: float = Field(default=0.0, alias="bonusApplied")


class CartValidation(SilpoModel):
    """A cart validation message (e.g. out-of-stock, slot conflict)."""

    code: str
    message: str
    severity: str = "warning"
    product_id: str | None = Field(default=None, alias="productId")


class SilpoCart(SilpoModel):
    """The full shopping cart."""

    cart_id: str = Field(alias="cartId")
    branch_id: str = Field(alias="branchId")
    delivery_type: str = Field(alias="deliveryType")
    timeslot: str | dict[str, Any] | None = None
    address: str | dict[str, Any] | None = None
    items: list[CartItem] = Field(default_factory=list)
    totals: CartTotals
    loyalty: CartLoyalty = Field(default_factory=CartLoyalty)
    validations: list[CartValidation] = Field(default_factory=list)
    checkout_web_link: str | None = Field(default=None, alias="checkoutWebLink")
    checkout_mobile_link: str | None = Field(default=None, alias="checkoutMobileLink")
    coupon_code: str | None = Field(default=None, alias="couponCode")
    promo_code: str | None = Field(default=None, alias="promoCode")


class CartSummary(SilpoModel):
    """Minimal cart identifier, from ``silpo_get_my_shopping_cart``.

    The server returns ``exists: false`` when the guest has no cart yet —
    in that case call ``silpo_create_shopping_cart``. Otherwise it returns
    the cart id as ``cartId`` (mock/documented) or ``shoppingCartId`` (live).
    """

    cart_id: str | None = Field(default=None, alias="cartId")
    shopping_cart_id: str | None = Field(default=None, alias="shoppingCartId")
    exists: bool = True

    @property
    def resolved_cart_id(self) -> str | None:
        """Return whichever cart id variant the server provided, if any."""
        return self.shopping_cart_id or self.cart_id


class CreateShoppingCartResult(SilpoModel):
    """Result of ``silpo_create_shopping_cart``."""

    success: bool = True
    summary: str | None = None
    shopping_cart_id: str = Field(alias="shoppingCartId")


class CartLineInput(SilpoModel):
    """A product line to add/update in the cart."""

    product_id: str = Field(alias="productId")
    company_id: str = Field(alias="companyId")
    branch_id: str = Field(alias="branchId")
    quantity: float = 1.0


class CartUpdateResult(SilpoModel):
    """Result of a cart mutation."""

    cart: SilpoCart
    changed: bool = True
