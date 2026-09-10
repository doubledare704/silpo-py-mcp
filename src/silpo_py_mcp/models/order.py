"""Order, profile, and loyalty models."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, model_validator

from silpo_py_mcp.models.base import SilpoModel


class OrderLine(SilpoModel):
    """A product line in an order (documented/mock shape)."""

    product_id: str = Field(alias="productId")
    title: str
    quantity: float
    unit_price: float = Field(alias="unitPrice")
    total_price: float = Field(alias="totalPrice")


class OnlineOrderItem(SilpoModel):
    """A product line in a live online order (``products[]``)."""

    product_id: str = Field(validation_alias=AliasChoices("productId", "id"))
    title: str = Field(default="", validation_alias=AliasChoices("title", "name"))
    quantity: float = 0
    unit_price: float = Field(default=0.0, validation_alias=AliasChoices("unitPrice", "price"))
    total_price: float = Field(default=0.0, validation_alias=AliasChoices("totalPrice", "subtotal"))
    removed: bool | None = None
    image: str | None = None
    company_id: str | None = Field(default=None, alias="companyId")
    branch_id: str | None = Field(default=None, alias="branchId")


class OnlineOrder(SilpoModel):
    """An online order from ``silpo_get_my_online_orders``.

    Live shape uses ``amount``/``products``/``delivery``/``address``; the
    legacy ``totalPrice``/``items``/``deliveryType`` aliases are kept for
    backward compatibility.
    """

    order_id: str = Field(alias="orderId")
    number: str | None = None
    created_at: str = Field(alias="createdAt")
    status: str
    amount: float | None = None
    total_price: float | None = Field(default=None, alias="totalPrice")
    discount: float = 0.0
    delivery_type: str | None = Field(default=None, alias="deliveryType")
    delivery: dict[str, Any] | None = None
    address: dict[str, Any] | None = None
    items: list[OnlineOrderItem] = Field(default_factory=list, validation_alias=AliasChoices("products", "items"))

    @model_validator(mode="after")
    def _fill_total(self) -> OnlineOrder:
        if self.total_price is None:
            self.total_price = self.amount
        return self


class OfflineReceiptItem(SilpoModel):
    """A product line in a live offline receipt (``products[]``)."""

    lager_id: float | int | None = Field(default=None, alias="lagerId")
    name: str = ""
    unit: str | None = None
    quantity: float = 0
    price: float = 0.0
    image: str | None = None
    catalog_product: dict[str, Any] | None = Field(default=None, alias="catalogProduct")
    product_id: str | None = Field(default=None, alias="productId")
    title: str | None = None
    unit_price: float | None = Field(default=None, alias="unitPrice")
    total_price: float | None = Field(default=None, alias="totalPrice")


class OfflineReceipt(SilpoModel):
    """A physical-store receipt from ``silpo_get_my_offline_orders``.

    Live shape uses ``filId``/``filialName``/``sumReg``/``products``; legacy
    ``receiptId``/``branchName``/``totalPrice``/``items`` aliases are kept.
    """

    receipt_id: str | None = Field(default=None, validation_alias=AliasChoices("receiptId", "id"))
    fil_id: float | int | None = Field(default=None, alias="filId")
    branch_name: str | None = Field(default=None, validation_alias=AliasChoices("branchName", "filialName"))
    city_name: str | None = Field(default=None, alias="cityName")
    purchased_at: str | None = Field(default=None, validation_alias=AliasChoices("purchasedAt", "createdAt"))
    total_price: float | None = Field(default=None, validation_alias=AliasChoices("totalPrice", "sumReg"))
    discount: float = Field(default=0.0, validation_alias=AliasChoices("discount", "sumDiscount"))
    bonuses_earned: float = Field(default=0.0, validation_alias=AliasChoices("bonusesEarned", "accruedBalaBonusesSum"))
    receipt_url: str | None = Field(default=None, alias="receiptUrl")
    cheque_magic_name: str | None = Field(default=None, alias="chequeMagicName")
    cheque_prediction: str | None = Field(default=None, alias="chequePrediction")
    rewards: list[dict[str, Any]] = Field(default_factory=list)
    items: list[OfflineReceiptItem] = Field(default_factory=list, validation_alias=AliasChoices("items", "products"))


class Profile(SilpoModel):
    """The guest's profile."""

    id: str | None = None
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
    floor: str | None = None
    entrance: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    comment: str | None = None


class FamilyMember(SilpoModel):
    """A family member in the profile (live ``members[]`` shape)."""

    profile_id: str | None = Field(default=None, alias="profileId")
    member_type: str | None = Field(default=None, alias="memberType", description="child | pet (legacy)")
    name: str | None = None
    age: int | None = None
    phone: str | None = None
    image: str | None = None
    profile_created_at: str | None = Field(default=None, alias="profileCreatedAt")
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
    """A discount coupon from ``silpo_get_my_coupons`` (live shape)."""

    coupon_id: str | int | float = Field(validation_alias=AliasChoices("couponId", "id"))
    title: str = ""
    description: str | None = None
    discount: float = 0.0
    expires_at: str | None = Field(default=None, validation_alias=AliasChoices("expiresAt", "endDateTime"))
    barcode: str | None = None
    active: bool | None = None
    use_way: str | None = Field(default=None, alias="useWay")
    begin_date: str | None = Field(default=None, alias="beginDate")
    end_date: str | None = Field(default=None, alias="endDate")
    limit_text: str | None = Field(default=None, alias="limitText")
    warning_text: str | None = Field(default=None, alias="warningText")
    image: str | None = None
    promo_id: float | int | None = Field(default=None, alias="promoId")
    reward_text: str | None = Field(default=None, alias="rewardText")
    reward_value: float | None = Field(default=None, alias="rewardValue")
    reward_unit: str | None = Field(default=None, alias="rewardUnit")
    reward_sign: str | None = Field(default=None, alias="rewardSign")
    reward_limit: float | None = Field(default=None, alias="rewardLimit")


class CouponProgress(SilpoModel):
    """Accumulation progress toward a coupon's spend/quantity threshold."""

    current: float = 0.0
    target: float = 0.0
    percent: float = 0.0
    unit: str | None = None


class CouponDetail(SilpoModel):
    """Full coupon information from ``silpo_get_coupon_details`` (live shape).

    ``can_be_applied_to_order`` is the single eligibility field: true only
    when the user toggle (``active``) is on and the lifecycle ``state`` is
    ``"Активний"``. Legacy ``conditions``/``productIds``/``barcode`` fields
    are kept for backward compatibility with older fixtures.
    """

    id: float | int | str | None = None
    coupon_id: str | int | None = Field(default=None, alias="couponId")
    business_coupon_id: int | None = Field(default=None, alias="businessCouponId")
    title: str = ""
    active: bool | None = None
    state: str | None = None
    can_be_applied_to_order: bool | None = Field(default=None, alias="canBeAppliedToOrder")
    use_way: str | None = Field(default=None, alias="useWay")
    begin_date: str | None = Field(default=None, alias="beginDate")
    end_date: str | None = Field(default=None, alias="endDate")
    end_date_time: str | None = Field(default=None, alias="endDateTime")
    used_count: float | None = Field(default=None, alias="usedCount")
    description: str | None = None
    limit_text: str | None = Field(default=None, alias="limitText")
    warning_text: str | None = Field(default=None, alias="warningText")
    reward_text: str | None = Field(default=None, alias="rewardText")
    reward_value: float | None = Field(default=None, alias="rewardValue")
    image: str | None = None
    promo_id: float | int | None = Field(default=None, alias="promoId")
    reward_unit: str | None = Field(default=None, alias="rewardUnit")
    reward_sign: str | None = Field(default=None, alias="rewardSign")
    reward_limit: float | None = Field(default=None, alias="rewardLimit")
    progress: CouponProgress | None = None
    conditions: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list, alias="productIds")
    barcode: str | None = None

    @model_validator(mode="after")
    def _fill_business_id(self) -> CouponDetail:
        if self.business_coupon_id is None and isinstance(self.id, (int, float)):
            self.business_coupon_id = int(self.id)
        return self


class Promo(SilpoModel):
    """A personalized promo offer from ``silpo_get_my_promos`` (live shape)."""

    promo_id: str | int | float = Field(validation_alias=AliasChoices("promoId", "id"))
    selected: bool | None = None
    title: str = ""
    description: str | None = None
    begin_date: str | None = Field(default=None, alias="beginDate")
    end_date: str | None = Field(default=None, alias="endDate")
    expires_at: str | None = Field(default=None, alias="expiresAt")
    reward_text: str | None = Field(default=None, alias="rewardText")
    reward_value: float | None = Field(default=None, alias="rewardValue")
    limit_text: str | None = Field(default=None, alias="limitText")
    warning_text: str | None = Field(default=None, alias="warningText")
    address_list_text: str | None = Field(default=None, alias="addressListText")
    image: str | None = None


class PromoCode(SilpoModel):
    """An active promo code from ``silpo_get_promo_codes`` (live shape)."""

    id: str | None = None
    code: str
    title: str | None = None
    active: bool | None = None
    description: str | None = None
    expires_at: str | None = Field(default=None, alias="expiresAt")


class Certificate(SilpoModel):
    """A gift certificate from ``silpo_get_my_certificates`` (live shape)."""

    id: float | int | str | None = None
    certificate_id: str | None = Field(default=None, alias="certificateId")
    code: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    total_price: float | None = Field(default=None, alias="totalPrice")
    barcode: str | None = None
    pincode: str | int | None = None
    expire_date: str | None = Field(default=None, alias="expireDate")
    title: str | None = None
    image: str | None = None
    nominal: float | None = None
    balance: float | None = None
    expires_at: str | None = Field(default=None, alias="expiresAt")


class SubscriptionFeature(SilpoModel):
    """A single Premium subscription feature card."""

    id: str | None = None
    business: str | None = None
    name: str | None = None
    checkout_text: str | None = Field(default=None, alias="checkoutText")
    image: str | None = None
    balance: dict[str, Any] | None = None
    web_link: str | None = Field(default=None, alias="webLink")
    mobile_link: str | None = Field(default=None, alias="mobileLink")
    description_html: str | None = Field(default=None, alias="descriptionHtml")


class PremiumSubscription(SilpoModel):
    """Silpo Premium subscription status (live shape)."""

    id: str | None = None
    profile_id: str | None = Field(default=None, alias="profileId")
    subscription_id: str | None = Field(default=None, alias="subscriptionId")
    created_at: str | None = Field(default=None, alias="createdAt")
    status: str | None = None
    date_from: str | None = Field(default=None, alias="dateFrom")
    date_to: str | None = Field(default=None, alias="dateTo")
    features: list[SubscriptionFeature] | None = None
    bonuses_obtained_amount: float | None = Field(default=None, alias="bonusesObtainedAmount")
    share_web_link: str | None = Field(default=None, alias="shareWebLink")
    share_mobile_link: str | None = Field(default=None, alias="shareMobileLink")
    web_link: str | None = Field(default=None, alias="webLink")
    mobile_link: str | None = Field(default=None, alias="mobileLink")
    is_active: bool | None = Field(default=False, alias="isActive")
    ends_at: str | None = Field(default=None, alias="endsAt")
    benefits: list[str] = Field(default_factory=list)
