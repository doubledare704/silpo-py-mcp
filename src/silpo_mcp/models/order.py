"""Order, profile, and loyalty models."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from silpo_mcp.models.base import SilpoModel


class OrderLine(SilpoModel):
    """A product line in an order."""

    product_id: str = Field(alias="productId")
    title: str
    quantity: float
    unit_price: float = Field(alias="unitPrice")
    total_price: float = Field(alias="totalPrice")


class OnlineOrder(SilpoModel):
    """An online order from ``silpo_get_my_online_orders``."""

    order_id: str = Field(alias="orderId")
    created_at: str = Field(alias="createdAt")
    status: str
    total_price: float = Field(alias="totalPrice")
    delivery_type: str | None = Field(default=None, alias="deliveryType")
    items: list[OrderLine] = Field(default_factory=list)


class OfflineReceipt(SilpoModel):
    """A physical-store receipt from ``silpo_get_my_offline_orders``."""

    receipt_id: str = Field(alias="receiptId")
    branch_name: str | None = Field(default=None, alias="branchName")
    purchased_at: str = Field(alias="purchasedAt")
    total_price: float = Field(alias="totalPrice")
    discount: float = Field(default=0.0)
    bonuses_earned: float = Field(default=0.0, alias="bonusesEarned")
    items: list[OrderLine] = Field(default_factory=list)


class Profile(SilpoModel):
    """The guest's profile."""

    name: str | None = None
    phone: str | None = None
    email: str | None = None
    birth_date: str | None = Field(default=None, alias="birthDate")


class DeliveryAddress(SilpoModel):
    """A saved delivery address."""

    address_id: str = Field(alias="addressId")
    label: str | None = None
    text: str
    coordinates: dict[str, float] | None = None


class FamilyMember(SilpoModel):
    """A family member in the profile."""

    member_type: str = Field(alias="memberType", description="child | pet")
    name: str | None = None
    age: int | None = None


class FoodRestrictions(SilpoModel):
    """Dietary restrictions and food preferences."""

    restrictions: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)


class LoyaltyInfo(SilpoModel):
    """Vlasnyi Rakunok (own account) loyalty card."""

    card_number: str = Field(alias="cardNumber")
    status: str
    bonus_balance: float = Field(alias="bonusBalance")
    bonus_earned: float = Field(default=0.0, alias="bonusEarned")
    extra: dict[str, Any] = Field(default_factory=dict)


class Coupon(SilpoModel):
    """A discount coupon."""

    coupon_id: str = Field(alias="couponId")
    title: str
    discount: float = 0.0
    expires_at: str | None = Field(default=None, alias="expiresAt")
    barcode: str | None = None


class CouponDetail(SilpoModel):
    """Full coupon information: conditions, products, barcode."""

    description: str | None = None
    conditions: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list, alias="productIds")


class Promo(SilpoModel):
    """A personalized promo offer."""

    promo_id: str = Field(alias="promoId")
    title: str
    description: str | None = None
    expires_at: str | None = Field(default=None, alias="expiresAt")


class PromoCode(SilpoModel):
    """An active promo code."""

    code: str
    description: str | None = None
    expires_at: str | None = Field(default=None, alias="expiresAt")


class Certificate(SilpoModel):
    """A gift certificate."""

    certificate_id: str = Field(alias="certificateId")
    code: str
    barcode: str | None = None
    nominal: float
    balance: float | None = None
    expires_at: str | None = Field(default=None, alias="expiresAt")


class PremiumSubscription(SilpoModel):
    """Silpo Premium subscription status."""

    is_active: bool = Field(alias="isActive")
    ends_at: str | None = Field(default=None, alias="endsAt")
    benefits: list[str] = Field(default_factory=list)
