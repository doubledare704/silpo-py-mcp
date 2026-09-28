"""Location, branch, delivery and time-slot models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, Field, model_validator

from silpo_py_mcp.models.base import SilpoModel


class GeoPoint(SilpoModel):
    """Latitude/longitude coordinates."""

    lat: float
    lng: float


class Address(SilpoModel):
    """A resolved street address returned by the Silpo API.

    Since server release-1.111.1 an unmatched house number no longer returns
    a silent ``success: true`` — the response flags it via ``warning``/
    ``houseNumberMatched``. Always check ``warning`` (or
    ``house_number_matched is False``) before geocoding-dependent calls.
    """

    address: str = ""
    city: str | None = None
    street: str | None = None
    house_number: str | None = Field(default=None, alias="houseNumber")
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    warning: str | None = Field(
        default=None,
        description="release-1.111.1: set when the house number could not be matched.",
    )
    house_number_matched: bool | None = Field(
        default=None,
        alias="houseNumberMatched",
        description="release-1.111.1: False when the house number is unmatched.",
    )

    @property
    def text(self) -> str:
        return self.address

    @property
    def coordinates(self) -> GeoPoint | None:
        if self.latitude is not None and self.longitude is not None:
            return GeoPoint(lat=self.latitude, lng=self.longitude)
        return None


class DeliveryType(StrEnum):
    """Supported delivery types returned by Silpo.

    Mirrors the live ``deliveryType`` enum from ``tools/list``.
    """

    UNKNOWN = "Unknown"
    SELF_PICKUP = "SelfPickup"
    DELIVERY_HOME = "DeliveryHome"
    DELIVERY_FLAT = "DeliveryFlat"
    DELIVERY_OFFICE = "DeliveryOffice"
    DELIVERY_GLOVO = "DeliveryGlovo"
    DELIVERY_EXPRESS = "DeliveryExpress"
    DELIVERY_EXPRESS_FOOD = "DeliveryExpressFood"
    JUST_IN = "JustIn"
    LONG_DELIVERY = "LongDelivery"
    JUST_IN_POST = "JustInPost"
    NOVA_POSHTA = "NovaPoshta"
    DELIVERY_EXPRESS_BY_PROMISE = "DeliveryExpressByPromise"
    WIDE_ASSORT = "WideAssortDelivery"
    B2B = "B2B"
    PRE_ORDER = "PreOrder"


class TimeSlotDeliveryType(StrEnum):
    """Delivery types accepted by ``silpo_get_time_slots`` (release-1.111.2).

    The server narrowed the ``deliveryTypes``/``deliveryType`` enum for the
    time-slots tool: it is a strict subset of :class:`DeliveryType`. Values
    such as ``Unknown``/``JustIn``/``JustInPost`` now fail schema validation
    with ``-32602``, while ``B2B`` is accepted again.
    """

    SELF_PICKUP = "SelfPickup"
    DELIVERY_HOME = "DeliveryHome"
    DELIVERY_EXPRESS = "DeliveryExpress"
    LONG_DELIVERY = "LongDelivery"
    NOVA_POSHTA = "NovaPoshta"
    DELIVERY_EXPRESS_BY_PROMISE = "DeliveryExpressByPromise"
    WIDE_ASSORT = "WideAssortDelivery"
    B2B = "B2B"
    PRE_ORDER = "PreOrder"


class UpdateCartDeliveryType(StrEnum):
    """Delivery types accepted by ``silpo_update_shopping_cart`` (release-1.111.3).

    A third, narrower enum: the update tool refuses the historical/express
    variants (``Unknown``/``JustIn``/``JustInPost``/``DeliveryFlat``/…) and
    takes only the eight types a cart can actually be scheduled with. It is a
    subset of :class:`DeliveryType` and of :class:`TimeSlotDeliveryType` minus
    ``DeliveryExpress``.
    """

    SELF_PICKUP = "SelfPickup"
    DELIVERY_HOME = "DeliveryHome"
    LONG_DELIVERY = "LongDelivery"
    DELIVERY_EXPRESS_BY_PROMISE = "DeliveryExpressByPromise"
    WIDE_ASSORT = "WideAssortDelivery"
    B2B = "B2B"
    PRE_ORDER = "PreOrder"
    NOVA_POSHTA = "NovaPoshta"


class AvailableDeliveryType(SilpoModel):
    """A delivery option for a given coordinate."""

    type: DeliveryType = Field(validation_alias=AliasChoices("type", "deliveryType"))
    branch_id: str | None = Field(default=None, alias="branchId")
    description: str | None = None
    min_order: float | None = Field(default=None, alias="minOrder")


class Branch(SilpoModel):
    """A Silpo store (branch).

    Accepts both the mock shape (``name`` + ``coordinates`` object) and the
    real-server shape (``city``/``address`` + top-level ``latitude``/``longitude``
    strings, ``companyId``/``externalId``/``open``). Missing ``name`` is derived
    from ``city``/``address`` and missing ``coordinates`` from
    ``latitude``/``longitude``.
    """

    branch_id: str = Field(alias="branchId")
    name: str = ""
    address: str | None = None
    city: str | None = None
    company_id: str | None = Field(default=None, alias="companyId")
    external_id: str | None = Field(default=None, alias="externalId")
    latitude: float | None = None
    longitude: float | None = None
    coordinates: GeoPoint | None = None
    has_pickup: bool = Field(default=False, alias="hasPickup")
    has_nova_poshta: bool = Field(default=False, alias="hasNovaPoshta")
    is_open: bool | None = Field(default=None, alias="open")
    open_hours: dict[str, str] | None = Field(default=None, alias="openHours")

    @model_validator(mode="before")
    @classmethod
    def _normalize_nulls(cls, data: object) -> object:
        if isinstance(data, dict):
            data = dict(data)
            if data.get("hasPickup") is None:
                data["hasPickup"] = False
            nova = data.get("hasNovaPoshta")
            if nova is None:
                nova = data.get("hasNP")
            data["hasNovaPoshta"] = bool(nova)
        return data

    @model_validator(mode="after")
    def _fill_derived(self) -> Branch:
        if self.coordinates is None and self.latitude is not None and self.longitude is not None:
            self.coordinates = GeoPoint(lat=self.latitude, lng=self.longitude)
        if self.coordinates is not None:
            if self.latitude is None:
                self.latitude = self.coordinates.lat
            if self.longitude is None:
                self.longitude = self.coordinates.lng
        if not self.name:
            parts = [p for p in (self.city, self.address) if p]
            self.name = ", ".join(parts) if parts else self.branch_id
        return self

    @property
    def display_name(self) -> str:
        return self.name


class TimeSlot(SilpoModel):
    """A delivery time slot.

    Since server release-1.111.1 slots carry ``serviceFee`` — the SelfPickup
    "Сервісний збір" fee previously folded into the cart total with no line
    item (0 for home-delivery slots).

    Release-1.111.3 clarified the field semantics:

    * ``is_available`` is authoritative. A delivery type can report real
      ``delivery_cost``/``min_order_cost`` data while *every* slot has
      ``available=False`` — pricing presence does not mean the type is
      bookable right now, so always filter on ``is_available``.
    * ``min_order_cost`` is the minimum order amount for this slot and is
      only ever reported here — the cart does not repeat it.
    * ``service_fee`` is a *preview* of the SelfPickup fee for comparing
      delivery options. The amount actually charged to a cart is
      ``calculation.service_fee.total`` on ``silpo_get_shopping_cart_by_id``,
      which takes precedence once a cart exists.
    * ``starts_at``/``ends_at`` are **UTC** — convert to the guest's timezone
      before presenting them.
    """

    id: str = ""
    delivery_type: DeliveryType = Field(alias="deliveryType")
    branch_id: str = Field(default="", alias="branchId")
    starts_at: str = Field(validation_alias=AliasChoices("startsAt", "start"))
    ends_at: str = Field(validation_alias=AliasChoices("endsAt", "end"))
    price: float = 0.0
    is_available: bool = Field(default=True, validation_alias=AliasChoices("isAvailable", "available"))
    is_express: bool = Field(default=False, alias="isExpress")
    delivery_cost: float | None = Field(default=None, alias="deliveryCost")
    service_fee: float | None = Field(default=None, alias="serviceFee")
    delivery_cost_map: list[dict[str, Any]] | None = Field(default=None, alias="deliveryCostMap")
    min_order_cost: float | None = Field(default=None, alias="minOrderCost")
    max_weight: float | None = Field(default=None, alias="maxWeight")
    constraints: dict[str, Any] | None = None
    fast: dict[str, Any] | None = None

    @property
    def is_bookable(self) -> bool:
        """Whether this slot can be picked right now (release-1.111.3)."""
        return self.is_available


class NovaPoshtaSettlement(SilpoModel):
    """A Nova Poshta settlement (city/town)."""

    settlement_id: str = Field(validation_alias=AliasChoices("settlementId", "id"))
    name: str = Field(validation_alias=AliasChoices("name", "title"))
    region: str | None = None
    area: str | None = None


class NovaPoshtaOffice(SilpoModel):
    """A Nova Poshta office or parcel machine."""

    office_id: str = Field(validation_alias=AliasChoices("officeId", "id"))
    name: str = Field(validation_alias=AliasChoices("name", "title"))
    address: str | None = None
    type: str | None = Field(default=None, description="office | postomat")
    coordinates: GeoPoint | None = None
    latitude: float | None = None
    longitude: float | None = None
    number: float | None = None
    status: str | None = None

    @model_validator(mode="after")
    def _fill_coordinates(self) -> NovaPoshtaOffice:
        if self.coordinates is None and self.latitude is not None and self.longitude is not None:
            self.coordinates = GeoPoint(lat=self.latitude, lng=self.longitude)
        return self
