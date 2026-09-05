"""Location, branch, delivery and time-slot models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from silpo_py_mcp.models.base import SilpoModel


class GeoPoint(SilpoModel):
    """Latitude/longitude coordinates."""

    lat: float
    lng: float


class Address(SilpoModel):
    """A resolved street address returned by the Silpo API."""

    address: str
    city: str | None = None
    street: str | None = None
    house_number: str | None = Field(default=None, alias="houseNumber")
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @property
    def text(self) -> str:
        return self.address

    @property
    def coordinates(self) -> GeoPoint | None:
        if self.latitude is not None and self.longitude is not None:
            return GeoPoint(lat=self.latitude, lng=self.longitude)
        return None


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
