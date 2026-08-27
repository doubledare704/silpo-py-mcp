"""Location, branch, delivery and time-slot models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from silpo_mcp.models.base import SilpoModel


class GeoPoint(SilpoModel):
    """Latitude/longitude coordinates."""

    lat: float
    lng: float


class Address(SilpoModel):
    """A resolved street address."""

    text: str
    coordinates: GeoPoint
    region: str | None = None
    city: str | None = None
    street: str | None = None
    house_number: str | None = Field(default=None, alias="houseNumber")


class DeliveryType(StrEnum):
    """Supported delivery types returned by Silpo."""

    DELIVERY_HOME = "DeliveryHome"
    WIDE_ASSORT = "WideAssortDelivery"
    SELF_PICKUP = "SelfPickup"
    NOVA_POSHTA = "NovaPoshta"
    B2B = "B2B"


class AvailableDeliveryType(SilpoModel):
    """A delivery option for a given coordinate."""

    type: DeliveryType
    branch_id: str | None = Field(default=None, alias="branchId")
    description: str | None = None
    min_order: float | None = Field(default=None, alias="minOrder")


class Branch(SilpoModel):
    """A Silpo store (branch)."""

    branch_id: str = Field(alias="branchId")
    name: str
    address: str | None = None
    coordinates: GeoPoint | None = None
    has_pickup: bool = Field(default=False, alias="hasPickup")
    has_nova_poshta: bool = Field(default=False, alias="hasNovaPoshta")
    open_hours: dict[str, str] | None = Field(default=None, alias="openHours")


class TimeSlot(SilpoModel):
    """A delivery time slot."""

    id: str
    delivery_type: DeliveryType = Field(alias="deliveryType")
    branch_id: str = Field(alias="branchId")
    starts_at: str = Field(alias="startsAt")
    ends_at: str = Field(alias="endsAt")
    price: float = 0.0
    is_available: bool = Field(default=True, alias="isAvailable")
    is_express: bool = Field(default=False, alias="isExpress")


class NovaPoshtaSettlement(SilpoModel):
    """A Nova Poshta settlement (city/town)."""

    settlement_id: str = Field(alias="settlementId")
    name: str
    region: str | None = None


class NovaPoshtaOffice(SilpoModel):
    """A Nova Poshta office or parcel machine."""

    office_id: str = Field(alias="officeId")
    name: str
    address: str | None = None
    type: str | None = Field(default=None, description="office | postomat")
    coordinates: GeoPoint | None = None
