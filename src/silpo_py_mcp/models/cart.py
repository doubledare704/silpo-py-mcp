"""Cart and checkout models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, Field, model_validator

from silpo_py_mcp.models.base import SilpoModel


def _amount_total(value: Any) -> float | None:
    """Read the ``total`` of a live ``{total, subTotal, subDiscount}`` amount.

    Since release-1.111.1/1.111.3 the server reports ``serviceFee`` as such an
    object while older responses used a bare number.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        total = value.get("total")
        if isinstance(total, (int, float)):
            return float(total)
    return None


def _merge_live_totals(totals: Any, calculation: dict[str, Any]) -> dict[str, Any]:
    """Overlay the live ``calculation`` sums onto the cart's ``totals``.

    The mock answers with its own ``totals``; the live server puts everything
    under ``calculation``. Since release-1.111.3 that block also carries
    ``totalAfterDiscounts`` (the amount the guest actually pays) and the
    delivery discount split, which are surfaced as first-class fields.
    """
    merged: dict[str, Any] = dict(totals) if isinstance(totals, dict) else {}
    delivery = calculation.get("delivery") if isinstance(calculation.get("delivery"), dict) else {}
    defaults = {
        "totalPrice": calculation.get("total", 0.0),
        "totalAfterDiscounts": calculation.get("totalAfterDiscounts", 0.0),
        "itemsPrice": calculation.get("productsTotal", calculation.get("subTotal", 0.0)),
        "deliveryPrice": delivery.get("total", 0.0),
        "deliverySubTotal": delivery.get("subTotal", 0.0),
        "deliveryDiscount": delivery.get("subDiscount", 0.0),
        "discount": calculation.get("subDiscount", 0.0),
        "certificatesTotal": calculation.get("certificatesTotal", 0.0),
    }
    for key, value in defaults.items():
        if not merged.get(key) and value:
            merged[key] = value
    service_fee = _amount_total(calculation.get("serviceFee"))
    if service_fee is not None and merged.get("serviceFee") is None:
        merged["serviceFee"] = service_fee
    return merged


def _lift_calculation(cart: dict[str, Any]) -> dict[str, Any]:
    """Lift the live ``calculation`` block onto the top level of a cart dict.

    The live server reports sums, the delivery discount split, the payment
    method list and the validations under ``calculation``; the client exposes
    them as typed fields on :class:`SilpoCart`. Runs as a before-validator so
    every path that parses a cart dict gets it — the wrapped live response, the
    flat mock cart, and the cart echoed back by the mock's mutation tools.
    """
    calculation = cart.get("calculation")
    if not isinstance(calculation, dict):
        return cart
    if isinstance(calculation.get("validations"), list):
        cart["validations"] = calculation["validations"]
    if cart.get("serviceFee") is None and calculation.get("serviceFee") is not None:
        cart["serviceFee"] = _amount_total(calculation.get("serviceFee"))
    for key in ("payment", "delivery"):
        if isinstance(calculation.get(key), dict):
            cart[key] = calculation[key]
    if cart.get("loyalty") is None and isinstance(calculation.get("loyalty"), dict):
        cart["loyalty"] = calculation["loyalty"]
    cart["totals"] = _merge_live_totals(cart.get("totals"), calculation)
    return cart


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
    """Monetary totals of the cart.

    ``total_price`` is the order total *before* discounts;
    ``total_after_discounts`` is what the user actually pays — always show the
    latter to the user (release-1.111.3). The delivery breakdown is
    ``delivery_price`` (the discounted cost the guest pays) out of
    ``delivery_sub_total``, with ``delivery_discount`` covering the difference.
    """

    total_price: float = Field(default=0.0, alias="totalPrice")
    total_after_discounts: float = Field(default=0.0, alias="totalAfterDiscounts")
    items_price: float = Field(default=0.0, alias="itemsPrice")
    delivery_price: float = Field(default=0.0, alias="deliveryPrice")
    delivery_sub_total: float = Field(default=0.0, alias="deliverySubTotal")
    delivery_discount: float = Field(default=0.0, alias="deliveryDiscount")
    discount: float = Field(default=0.0)
    certificates_total: float = Field(default=0.0, alias="certificatesTotal")
    service_fee: float | None = Field(default=None, alias="serviceFee")
    bonuses_to_apply: float = Field(default=0.0, alias="bonusesToApply")


class CartAddressType(StrEnum):
    """``addressType`` values accepted on a cart address (release-1.111.3).

    Required on the ``address`` object of ``silpo_update_shopping_cart`` and on
    ``silpo_create_shopping_cart``. The live server expects the whole address
    object copied from the cart response — ``self-pickup`` addresses are built
    from ``silpo_list_branches`` and ``nova-poshta`` ones from the Nova Poshta
    office, while the remaining values come from ``silpo_find_address``.
    """

    SELF_PICKUP = "self-pickup"
    HOUSE = "house"
    FLAT = "flat"
    OFFICE = "office"
    POINT = "point"
    NOVA_POSHTA = "nova-poshta"


class CartAmount(SilpoModel):
    """A three-way amount breakdown: ``total``/``subTotal``/``subDiscount``."""

    total: float = 0.0
    sub_total: float = Field(default=0.0, alias="subTotal")
    sub_discount: float = Field(default=0.0, alias="subDiscount")


class CartLoanConfig(SilpoModel):
    """BNPL ("buy now, pay later") terms attached to a payment method."""

    buffer_percent: float = Field(default=0.0, alias="bufferPercent")
    min_total: float = Field(default=0.0, alias="minTotal")
    payment_count: int = Field(default=0, alias="paymentCount")


class CartLoan(SilpoModel):
    """BNPL availability for a cart or a single payment method.

    A ``False`` ``loan_available`` on a method whose ``available`` is also
    ``False`` normally means the order is below ``loan_config.min_total``
    (e.g. BNPL needs ₴1000) — the same reason is echoed in
    ``validations`` as ``order.payment_types.disabled``.
    """

    loan_available: bool = Field(default=False, alias="loanAvailable")
    loan_calculation: dict[str, Any] | None = Field(default=None, alias="loanCalculation")
    loan_config: CartLoanConfig | None = Field(default=None, alias="loanConfig")


class CartPaymentOption(SilpoModel):
    """One payment method and whether the guest can currently use it."""

    type: str
    available: bool = True
    loan: CartLoan | None = None


class CartPayment(SilpoModel):
    """Payment methods offered for the cart (release-1.111.3).

    ``types`` is the authoritative list of every method with its
    availability — read it instead of the top-level ``cart.paymentType``,
    which only reflects the method actually selected so far and stays
    ``"Unknown"`` until the guest picks one at checkout. ``type`` is the
    currently effective method for the totals shown here.
    """

    type: str = "Unknown"
    types: list[CartPaymentOption] = Field(default_factory=list)
    loan: CartLoan | None = None

    @property
    def available_types(self) -> list[str]:
        """Names of the methods the guest can pick right now."""
        return [option.type for option in self.types if option.available]

    @property
    def unavailable_types(self) -> list[str]:
        """Names of the methods currently blocked (e.g. BNPL below minimum)."""
        return [option.type for option in self.types if not option.available]

    def option(self, name: str) -> CartPaymentOption | None:
        """Look up a single payment method by name (case-insensitive)."""
        lowered = name.lower()
        return next((opt for opt in self.types if opt.type.lower() == lowered), None)

    def is_available(self, name: str) -> bool:
        """Whether ``name`` is offered and currently usable."""
        found = self.option(name)
        return bool(found and found.available)


class CartDelivery(SilpoModel):
    """Delivery cost breakdown (``calculation.delivery``, release-1.111.3).

    ``sub_total`` is the flat/undiscounted delivery cost and ``sub_discount``
    how much of it was waived, so ``sub_total - sub_discount == total``. Do not
    assume a tier-based explanation for ``sub_discount``: order-total tiers
    (``get_time_slots`` ``slots[].deliveryCostMap``) are one cause, but premium
    subscription perks can override delivery cost independently of the order
    total.
    """

    total: float = 0.0
    sub_total: float = Field(default=0.0, alias="subTotal")
    sub_discount: float = Field(default=0.0, alias="subDiscount")
    total_weight: float = Field(default=0.0, alias="totalWeight")
    delivery_express_by_promise: dict[str, Any] | None = Field(default=None, alias="deliveryExpressByPromise")

    @property
    def discount_percent(self) -> float:
        """Share of the delivery cost that was discounted (0.0 when undiscounted)."""
        if self.sub_total <= 0.0:
            return 0.0
        return round(self.sub_discount / self.sub_total, 4)


class CartCalculation(SilpoModel):
    """``calculation`` — the cart's money and checkout state.

    ``total`` is the order total before discounts; ``total_after_discounts``
    is the amount the guest actually pays and is the number to show them.
    ``total == products_total + delivery.total + service_fee.total``.
    """

    total: float = 0.0
    total_after_discounts: float = Field(default=0.0, alias="totalAfterDiscounts")
    certificates_total: float = Field(default=0.0, alias="certificatesTotal")
    products_total: float = Field(default=0.0, alias="productsTotal")
    sub_total: float = Field(default=0.0, alias="subTotal")
    sub_discount: float = Field(default=0.0, alias="subDiscount")
    service_fee: CartAmount = Field(default_factory=CartAmount)
    delivery: CartDelivery = Field(default_factory=CartDelivery)
    payment: CartPayment = Field(default_factory=CartPayment)
    promo_code: str | None = Field(default=None, alias="promoCode")
    loyalty: CartLoyalty | None = None
    validations: list[CartValidation] = Field(default_factory=list)


class CartLoyalty(SilpoModel):
    """Loyalty state attached to the cart.

    ``bonus_total`` is the guest's whole balance while ``bonus_available`` is
    the part applicable to this cart — only offer to apply bonuses when
    ``bonus_requested is None``, ``bonus_total >= bonus_available`` and
    ``is_enabled`` is true.
    """

    is_enabled: bool = Field(default=False, alias="isEnabled")
    bonus_total: float = Field(default=0.0, alias="bonusTotal")
    bonus_available: float = Field(default=0.0, alias="bonusAvailable")
    bonus_requested: float | None = Field(default=None, alias="bonusRequested")
    bonus_applied: float = Field(default=0.0, alias="bonusApplied")

    @property
    def can_offer_bonuses(self) -> bool:
        """Whether it makes sense to ask the guest to pay with bonuses."""
        return self.is_enabled and self.bonus_requested is None and self.bonus_available > 0.0


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
    ``branch_id``/``totals``/``validations``). Since server release-1.111.1
    the cart carries ``serviceFee`` — the SelfPickup "Сервісний збір" fee
    previously folded into the total with no line item.

    Release-1.111.3 added the payment and delivery-discount surface:
    ``payment`` (every method with its availability, plus BNPL terms) and
    ``calculation.delivery.sub_total``/``sub_discount``. ``payment_type`` is
    the *selected* method and stays ``"Unknown"`` until the guest picks one —
    read ``payment.available_types`` to know what is actually on offer.
    """

    cart_id: str = Field(default="", validation_alias=AliasChoices("cartId", "id"))
    branch_id: str = Field(default="", alias="branchId")
    delivery_type: str = Field(default="", alias="deliveryType")
    timeslot: str | dict[str, Any] | None = None
    address: str | dict[str, Any] | None = None
    items: list[CartItem] = Field(default_factory=list)
    shipments: list[dict[str, Any]] = Field(default_factory=list)
    calculation: CartCalculation | None = None
    totals: CartTotals = Field(default_factory=CartTotals)
    service_fee: float | None = Field(default=None, alias="serviceFee")
    payment_type: str = Field(default="Unknown", alias="paymentType")
    payment: CartPayment = Field(default_factory=CartPayment)
    delivery: CartDelivery = Field(default_factory=CartDelivery)
    loyalty: CartLoyalty = Field(default_factory=CartLoyalty)
    validations: list[CartValidation] = Field(default_factory=list)
    checkout_web_link: str | None = Field(default=None, alias="checkoutWebLink")
    checkout_mobile_link: str | None = Field(default=None, alias="checkoutMobileLink")
    coupon_code: str | None = Field(default=None, alias="couponCode")
    promo_code: str | None = Field(default=None, alias="promoCode")

    @model_validator(mode="before")
    @classmethod
    def _apply_live_calculation(cls, data: object) -> object:
        if isinstance(data, dict):
            return _lift_calculation(dict(data))
        return data

    @property
    def total_to_pay(self) -> float:
        """What the guest actually pays — prefer this over ``totals.total_price``."""
        return self.totals.total_after_discounts or self.totals.total_price

    @property
    def available_payment_types(self) -> list[str]:
        """Payment methods usable right now (release-1.111.3)."""
        return self.payment.available_types

    @property
    def update_payloads(self) -> CartUpdatePayloads:
        """Ready-to-send ``address``/``shipments`` for ``update_shopping_cart``.

        Since release-1.111.3 the server requires ``address.addressType`` and a
        ``companyId``/``branchId`` pair per shipment, and instructs callers to
        copy both verbatim from the cart response rather than build them by
        hand. This property does exactly that, so a cart read can be handed
        straight back to ``update_shopping_cart``.
        """
        return CartUpdatePayloads.from_cart(self)


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
    add_quantity: bool | None = Field(default=None, alias="addQuantity")
    comment: str | None = None


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


class CartUpdatePayloads(SilpoModel):
    """The ``address``/``shipments``/``timeslot`` trio for a cart update.

    ``silpo_update_shopping_cart`` (release-1.111.3) requires
    ``address.addressType`` and a ``companyId``+``branchId`` pair on every
    shipment, and the server tells callers to copy these objects verbatim from
    ``silpo_get_shopping_cart_by_id`` instead of assembling them. Building them
    from a :class:`SilpoCart` keeps that copy-exactly contract mechanical::

        cart = await client.get_cart_by_id(cart_id)
        payloads = cart.update_payloads
        await client.update_shopping_cart(
            cart_id,
            cart.delivery_type,
            payloads.timeslot,
            payloads.address,
            payloads.shipments,
        )
    """

    address: dict[str, Any]
    shipments: list[dict[str, Any]]
    timeslot: dict[str, Any]
    delivery_type: str = ""
    missing_fields: list[str] = Field(default_factory=list)

    @classmethod
    def from_cart(cls, cart: SilpoCart) -> CartUpdatePayloads:
        """Extract the update payloads from a cart, recording what is missing.

        ``missing_fields`` lists the keys the live schema requires that the
        cart did not carry (e.g. an address without ``addressType``); an empty
        list means the trio is safe to send as-is.
        """
        address: dict[str, Any] = {}
        missing: list[str] = []
        if isinstance(cart.address, dict):
            address = dict(cart.address)
        if not address:
            missing.append("address")
        elif not address.get("addressType"):
            missing.append("address.addressType")

        shipments: list[dict[str, Any]] = []
        for index, shipment in enumerate(cart.shipments):
            if not isinstance(shipment, dict):
                continue
            entry = {key: shipment[key] for key in ("companyId", "branchId") if shipment.get(key)}
            for key in ("companyId", "branchId"):
                if key not in entry:
                    missing.append(f"shipments[{index}].{key}")
            if entry:
                shipments.append(entry)
        if not shipments:
            missing.append("shipments")

        timeslot: dict[str, Any] = {}
        if isinstance(cart.timeslot, dict):
            timeslot = {key: cart.timeslot[key] for key in ("start", "end") if cart.timeslot.get(key)}
        if not timeslot:
            missing.append("timeslot")

        return cls(
            address=address,
            shipments=shipments,
            timeslot=timeslot,
            delivery_type=cart.delivery_type,
            missing_fields=missing,
        )

    @property
    def is_sendable(self) -> bool:
        """Whether every field the live schema requires is present."""
        return not self.missing_fields
