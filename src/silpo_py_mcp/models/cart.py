"""Cart and checkout models."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, model_validator

from silpo_py_mcp.models.base import SilpoModel


class CartItem(SilpoModel):
    """A single product line in the cart."""

    product_id: str = Field(alias="productId")
    company_id: str = Field(default="", alias="companyId")
    branch_id: str = Field(default="", alias="branchId")
    title: str
    quantity: float
    unit_price: float = Field(default=0.0, alias="unitPrice")
    total_price: float = Field(default=0.0, alias="totalPrice")
    is_available: bool = Field(default=True, alias="isAvailable")


class CartTotals(SilpoModel):
    """Monetary totals of the cart."""

    total_price: float = Field(default=0.0, alias="totalPrice")
    items_price: float = Field(default=0.0, alias="itemsPrice")
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
    """A cart validation message.

    Accepts both the live shape (``level``/``type``/``message``/``context``,
    nested under ``calculation``) and the documented shape
    (``code``/``message``/``severity``).
    """

    code: str = ""
    message: str = ""
    severity: str = "warning"
    level: str | None = None
    validation_type: str | None = Field(default=None, alias="type")
    context: dict[str, Any] | list[Any] | None = None
    product_id: str | None = Field(default=None, alias="productId")

    @model_validator(mode="after")
    def _fill_from_live(self) -> CartValidation:
        if not self.code and self.validation_type:
            self.code = self.validation_type
        if self.level and self.severity == "warning":
            self.severity = self.level
        return self


class SilpoCart(SilpoModel):
    """The full shopping cart.

    The mock returns ``items``/``totals``/``branchId`` at the top level; the
    live server nests products under ``shipments[].products`` and sums under
    ``calculation`` (see ``SilpoClient.get_cart_by_id``, which maps those onto
    ``branch_id``/``totals``/``validations``).
    """

    cart_id: str = Field(default="", validation_alias=AliasChoices("cartId", "id"))
    branch_id: str = Field(default="", alias="branchId")
    delivery_type: str = Field(default="", alias="deliveryType")
    timeslot: str | dict[str, Any] | None = None
    address: str | dict[str, Any] | None = None
    items: list[CartItem] = Field(default_factory=list)
    shipments: list[dict[str, Any]] = Field(default_factory=list)
    calculation: dict[str, Any] | None = None
    totals: CartTotals = Field(default_factory=CartTotals)
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
    """Result of a cart mutation.

    The mock returns the full ``cart``; the live server returns only
    ``success``/``summary`` plus ``products``/``shoppingCartId``/``added``/
    ``removed`` — call ``get_cart_by_id`` afterwards to verify the cart.
    """

    success: bool = True
    summary: str | None = None
    cart: SilpoCart = Field(default_factory=SilpoCart)
    changed: bool = True
    products: list[dict[str, Any]] | None = None
    shopping_cart_id: str | None = Field(default=None, alias="shoppingCartId")
    added: list[Any] | None = None
    removed: list[str] | None = None
