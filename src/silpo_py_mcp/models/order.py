"""Order, profile, and loyalty models."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, model_validator

from silpo_py_mcp.models.base import SilpoModel


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
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    middle_name: str | None = Field(default=None, alias="middleName")
    birthday: str | None = None
    gender: str | None = None
    status: str | None = None

    @model_validator(mode="after")
    def _fill_name(self) -> Profile:
        if not self.name:
            self.name = " ".join(p for p in (self.first_name, self.last_name) if p) or None
        if self.birth_date is None:
            self.birth_date = self.birthday
        return self


class DeliveryAddress(SilpoModel):
    """A saved delivery address."""

    address_id: str = Field(validation_alias=AliasChoices("addressId", "id"))
    label: str | None = Field(default=None, validation_alias=AliasChoices("label", "tag"))
    text: str | None = None
    coordinates: dict[str, float] | None = None
    city: str | None = None
    street: str | None = None
    building: str | None = None
    apartment: str | None = None


class FamilyMember(SilpoModel):
    """A family member in the profile."""

    member_type: str | None = Field(default=None, alias="memberType", description="child | pet")
    name: str | None = None
    age: int | None = None
    profile_id: str | None = Field(default=None, alias="profileId")
    phone: str | None = None
    its_me: bool | None = Field(default=None, alias="itsMe")


class FoodRestrictions(SilpoModel):
    """Dietary restrictions and food preferences."""

    restrictions: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: object) -> object:
        if isinstance(data, dict) and isinstance(data.get("restrictions"), list):
            data = dict(data)
            data["restrictions"] = [
                item.get("slug") if isinstance(item, dict) else item for item in data["restrictions"]
            ]
        return data


class LoyaltyInfo(SilpoModel):
    """Vlasnyi Rakunok (own account) loyalty card."""

    card_number: str = Field(default="", alias="cardNumber")
    status: str = ""
    bonus_balance: float = Field(default=0.0, alias="bonusBalance")
    bonus_earned: float = Field(default=0.0, alias="bonusEarned")
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data: object) -> object:
        if isinstance(data, dict) and isinstance(data.get("card"), dict):
            card = data["card"]
            balance = data.get("balance")
            data = dict(data)
            data["cardNumber"] = card.get("barcode") or card.get("cardNumber") or ""
            data["status"] = card.get("typeName") or card.get("status") or ""
            if isinstance(balance, dict) and balance.get("total") is not None:
                data["bonusBalance"] = balance["total"]
            data.pop("card", None)
            data.pop("balance", None)
        return data


class Coupon(SilpoModel):
    """A discount coupon."""

    coupon_id: str | int = Field(validation_alias=AliasChoices("couponId", "id"))
    title: str = ""
    discount: float = 0.0
    expires_at: str | None = Field(default=None, validation_alias=AliasChoices("expiresAt", "endDateTime"))
    barcode: str | None = None
    active: bool | None = None
    use_way: str | None = Field(default=None, alias="useWay")
    begin_date: str | None = Field(default=None, alias="beginDate")
    end_date: str | None = Field(default=None, alias="endDate")


class CouponDetail(SilpoModel):
    """Full coupon information: conditions, products, barcode."""

    coupon_id: str | int | None = Field(default=None, validation_alias=AliasChoices("couponId", "id"))
    business_coupon_id: int | None = Field(default=None, alias="businessCouponId")
    title: str = ""
    description: str | None = None
    conditions: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list, alias="productIds")
    barcode: str | None = None


class Promo(SilpoModel):
    """A personalized promo offer."""

    promo_id: str = Field(validation_alias=AliasChoices("promoId", "id"))
    title: str = ""
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

    is_active: bool | None = Field(default=False, alias="isActive")
    ends_at: str | None = Field(default=None, alias="endsAt")
    benefits: list[str] = Field(default_factory=list)
    web_link: str | None = Field(default=None, alias="webLink")
    mobile_link: str | None = Field(default=None, alias="mobileLink")
    status: str | None = None
