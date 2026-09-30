"""In-memory FastMCP mock server implementing the Silpo ``silpo_*`` tools.

Used for development and testing without a live Silpo account. The mock
mirrors the 40 documented tools with realistic fixtures and per-client
cart state. Connect to it in-memory:

    from silpo_py_mcp.mock_server import SilpoMockServer
    from fastmcp import Client

    server = SilpoMockServer()
    client = Client(server.fastmcp)

The tool names, argument names and response keys intentionally follow the
documented Silpo schema (camelCase), so the same high-level client code works
against both the mock and the real server.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, ClassVar

from fastmcp import FastMCP
from fastmcp.server.context import Context

from silpo_py_mcp.models import TimeSlotDeliveryType, UpdateCartDeliveryType
from silpo_py_mcp.slot_time import parse_slot_bound as _parse_slot_bound

#: ``deliveryType`` values accepted by ``silpo_update_shopping_cart`` (release-1.111.3).
_UPDATE_CART_DELIVERY_TYPES: tuple[str, ...] = tuple(member.value for member in UpdateCartDeliveryType)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BRANCHES: list[dict[str, Any]] = [
    {
        "branchId": "bran-1",
        "name": "Сільпо Львів (центр)",
        "address": "вул. Степана Бандери, 3",
        "coordinates": {"lat": 49.8383, "lng": 24.0232},
        "hasPickup": True,
        "hasNovaPoshta": False,
        "openHours": {"mon-fri": "08:00-22:00", "sat-sun": "09:00-21:00"},
    },
    {
        "branchId": "bran-2",
        "name": "Сільпо Київ (позняки)",
        "address": "вул. Анни Ахматової, 9",
        "coordinates": {"lat": 50.3957, "lng": 30.6217},
        "hasPickup": True,
        "hasNovaPoshta": True,
        "openHours": {"mon-sun": "08:00-23:00"},
    },
]

PRODUCTS: list[dict[str, Any]] = [
    {
        "productId": "prd-milk-2pct",
        "companyId": "co-1",
        "branchId": "bran-1",
        "title": "Молоко Премія 2.5% 900 мл",
        "slug": "moloko-premiya-25-900-ml",
        "brand": "Премія",
        "price": 36.9,
        "displayPrice": 36.9,
        "oldPrice": None,
        "isOnSale": False,
        "isPrivateLabel": True,
        "isAvailable": True,
        "category": "Молочні продукти",
        "imageUrl": "https://images.silpo.ua/mock/milk.png",
        "unit": "шт",
        "stock": 10.0,
        "weighted": False,
        "step": 1.0,
        "displayRatio": "900мл",
        "specialPrices": None,
        "externalProductId": 100001,
    },
    {
        "productId": "prd-bread",
        "companyId": "co-2",
        "branchId": "bran-1",
        "title": "Хліб український нарізний",
        "slug": "hleb-ukrainskyi-nariznyi",
        "brand": "Київхліб",
        "price": 28.5,
        "displayPrice": 28.5,
        "oldPrice": None,
        "isOnSale": False,
        "isPrivateLabel": False,
        "isAvailable": True,
        "category": "Хліб та випічка",
        "imageUrl": "https://images.silpo.ua/mock/bread.png",
        "unit": "шт",
        "stock": 20.0,
        "weighted": False,
        "step": 1.0,
        "displayRatio": "500г",
        "specialPrices": None,
        "externalProductId": 100002,
    },
    {
        "productId": "prd-eggs",
        "companyId": "co-3",
        "branchId": "bran-1",
        "title": "Яйця курячі С1, 10 шт",
        "slug": "yaytsya-kuryachi-s1-10-sht",
        "brand": "Ясенсвіт",
        "price": 54.9,
        "displayPrice": 54.9,
        "oldPrice": 62.0,
        "isOnSale": True,
        "isPrivateLabel": False,
        "isAvailable": True,
        "category": "Яйця",
        "imageUrl": "https://images.silpo.ua/mock/eggs.png",
        "unit": "шт",
        "stock": 15.0,
        "weighted": False,
        "step": 1.0,
        "displayRatio": "10 шт",
        "specialPrices": None,
        "externalProductId": 100003,
    },
    {
        "productId": "prd-cheese",
        "companyId": "co-4",
        "branchId": "bran-1",
        "title": "Сир Гауда 45% 250 г",
        "slug": "syr-gauda-45-250-g",
        "brand": "Сир",
        "price": 89.0,
        "displayPrice": 89.0,
        "oldPrice": 110.0,
        "isOnSale": True,
        "isPrivateLabel": False,
        "isAvailable": True,
        "category": "Молочні продукти",
        "imageUrl": "https://images.silpo.ua/mock/cheese.png",
        "unit": "шт",
        "stock": 8.0,
        "weighted": False,
        "step": 1.0,
        "displayRatio": "250г",
        "specialPrices": [{"price": 80.0, "count": 2, "type": "bulk"}],
        "externalProductId": 100004,
    },
    {
        "productId": "prd-apples",
        "companyId": "co-5",
        "branchId": "bran-1",
        "title": "Яблука Гала, 1 кг",
        "slug": "yabluka-gala-1-kg",
        "brand": "Фрукти",
        "price": 42.0,
        "displayPrice": 42.0,
        "oldPrice": None,
        "isOnSale": False,
        "isPrivateLabel": False,
        "isAvailable": False,
        "category": "Фрукти та овочі",
        "imageUrl": "https://images.silpo.ua/mock/apples.png",
        "unit": "кг",
        "stock": 0.0,
        "weighted": True,
        "step": 0.5,
        "displayRatio": "1кг",
        "specialPrices": None,
        "externalProductId": 100005,
    },
]

CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "cat-dairy",
        "slug": "molochni",
        "title": "Молочні продукти",
        "parentId": None,
        "productCount": 2,
        "url": "https://silpo.ua/category/molochni",
    },
    {
        "id": "cat-bread",
        "slug": "hlib",
        "title": "Хліб та випічка",
        "parentId": None,
        "productCount": 1,
        "url": "https://silpo.ua/category/hlib",
    },
    {
        "id": "cat-eggs",
        "slug": "yaytsya",
        "title": "Яйця",
        "parentId": "cat-dairy",
        "productCount": 1,
        "url": "https://silpo.ua/category/yaytsya",
    },
    {
        "id": "cat-fruit",
        "slug": "frukti",
        "title": "Фрукти та овочі",
        "parentId": None,
        "productCount": 1,
        "url": "https://silpo.ua/category/frukti",
    },
]

PROMOTIONS: list[dict[str, Any]] = [
    {
        "code": "price-week-1",
        "title": "Ціна тижня: Яйця С1",
        "productCount": 1,
        "url": "https://silpo.ua/offers/price-week-1",
    },
    {
        "code": "cheese-15",
        "title": "Сир Гауда -15%",
        "productCount": 1,
        "url": "https://silpo.ua/offers/cheese-15",
    },
]

PRODUCT_SETS: list[dict[str, Any]] = [
    {
        "id": "set-1",
        "slug": "snidanok-150",
        "title": "Сніданок за 150 грн",
        "description": "Молоко, хліб, яйця — зберіть сніданок вигідно.",
        "link": "https://silpo.ua/sets/snidanok-150",
        "products": [PRODUCTS[0], PRODUCTS[1], PRODUCTS[2]],
    }
]

FIXTURE_ADDRESSES = [
    {
        "address": "Київ, вул. Анни Ахматової, 9",
        "city": "Київ",
        "street": "вул. Анни Ахматової",
        "houseNumber": "9",
        "district": "Печерськ",
        "latitude": 50.3957,
        "longitude": 30.6217,
    },
]

NOVA_POSHTA_SETTLEMENTS = [
    {
        "settlementId": "np-kyiv",
        "id": "np-kyiv",
        "name": "Київ",
        "title": "Київ",
        "region": "Київська обл.",
        "area": None,
    },
    {
        "settlementId": "np-lviv",
        "id": "np-lviv",
        "name": "Львів",
        "title": "Львів",
        "region": "Львівська обл.",
        "area": None,
    },
]

NOVA_POSHTA_OFFICES = [
    {
        "officeId": "np-office-1",
        "id": "np-office-1",
        "name": "Відділення №1",
        "title": "Відділення №1",
        "address": "вул. Центральна, 1",
        "type": "office",
        "number": 1,
        "status": "active",
        "latitude": 50.4501,
        "longitude": 30.5234,
    },
    {
        "officeId": "np-postomat-1",
        "id": "np-postomat-1",
        "name": "Поштомат біля метро",
        "title": "Поштомат біля метро",
        "address": "вул. Київська, 2",
        "type": "postomat",
        "number": 2,
        "status": "active",
        "latitude": 50.4510,
        "longitude": 30.5240,
    },
]


# ---------------------------------------------------------------------------
# Mock server
# ---------------------------------------------------------------------------


class SilpoMockServer:
    """FastMCP server that emulates the Silpo MCP endpoint in-memory."""

    _mock_carts: ClassVar[dict[str, str]] = {}

    def __init__(self) -> None:
        self._fastmcp = FastMCP("silpo-mock")
        self._carts: dict[str, dict[str, Any]] = {}
        self._favorites: list[str] = []
        self._register_tools()

    @property
    def fastmcp(self) -> FastMCP:
        return self._fastmcp

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _session_key(context: Context | None) -> str | None:
        """Return a stable per-session key, or None when no session exists."""
        if context is None:
            return None
        try:
            return context.session_id
        except RuntimeError:
            return None

    @staticmethod
    def _get_cartId(session_key: str | None) -> str | None:
        """Return the cart id scoped to the current session, or None."""
        if session_key is None:
            return None
        return SilpoMockServer._mock_carts.get(session_key)

    def _ensure_cart(self, session_key: str | None) -> str:
        carts = SilpoMockServer._mock_carts
        if session_key is None:
            session_key = f"anon-{uuid.uuid4().hex[:8]}"
        cartId = carts.get(session_key)
        if cartId is None or cartId not in self._carts:
            cartId = f"cart-{uuid.uuid4().hex[:8]}"
            self._carts[cartId] = self._new_cart(
                cartId,
                "DeliveryHome",
                {
                    "addressType": "house",
                    "address": "проспект Петра Григоренка, 22/20",
                    "city": "Київ",
                    "latitude": str(FIXTURE_ADDRESSES[0].get("latitude", "")),
                    "longitude": str(FIXTURE_ADDRESSES[0].get("longitude", "")),
                },
                [{"companyId": "co-1", "branchId": "bran-1"}],
            )
            carts[session_key] = cartId
        return cartId

    def _new_cart(
        self,
        cart_id: str,
        delivery_type: str,
        address: dict[str, Any],
        shipments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build an empty cart that is already valid input for a cart update.

        Since release-1.111.3 ``silpo_update_shopping_cart`` requires an
        ``address.addressType`` and a ``companyId``/``branchId`` pair per
        shipment, and the server wants both copied verbatim from the cart — so
        a fresh mock cart carries them from the start and
        ``cart.update_payloads`` round-trips.
        """
        fee = self._service_fee_for(delivery_type)
        cart: dict[str, Any] = {
            "cartId": cart_id,
            "branchId": shipments[0]["branchId"] if shipments else "bran-1",
            "deliveryType": delivery_type,
            "timeslot": {"start": "2026-09-02T08:00:00+00:00", "end": "2026-09-02T10:00:00+00:00"},
            "address": address,
            "shipments": shipments,
            "items": [],
            "totals": {
                "totalPrice": 0.0,
                "itemsPrice": 0.0,
                "deliveryPrice": 0.0,
                "discount": 0.0,
                "serviceFee": fee,
            },
            "serviceFee": fee,
            "paymentType": "Unknown",
            "loyalty": {
                "isEnabled": True,
                "bonusTotal": 125.5,
                "bonusAvailable": 125.5,
                "bonusRequested": None,
                "bonusApplied": 0.0,
            },
            "validations": [],
            "checkoutWebLink": f"https://silpo.ua/cart/{cart_id}",
            "checkoutMobileLink": f"silpo://cart/{cart_id}",
        }
        self._build_calculation(cart)
        return cart

    @staticmethod
    def _service_fee_for(delivery_type: str) -> float:
        """SelfPickup "Сервісний збір" fee (release-1.111.1); 0 otherwise."""
        return 15.0 if delivery_type == "SelfPickup" else 0.0

    #: Payment methods the mock offers, in the live order (release-1.111.3).
    PAYMENT_TYPES: tuple[str, ...] = (
        "Cashdesk",
        "Card",
        "Masterpass",
        "ApplePay",
        "GooglePay",
        "BVR",
        "B2B",
        "BNPL",
    )
    #: BNPL minimum order total, as in the live ``loanConfig``.
    BNPL_MIN_TOTAL = 1000.0

    @staticmethod
    def _payment_block(total: float) -> dict[str, Any]:
        """Build ``calculation.payment`` (release-1.111.3).

        Every method is listed with its availability; BNPL is blocked below
        :attr:`BNPL_MIN_TOTAL`, mirroring the live ``order.payment_types.disabled``
        validation. ``type`` stays ``"Unknown"`` until a method is selected at
        checkout — it reflects the selection, not what is on offer.
        """
        bnpl_available = total >= SilpoMockServer.BNPL_MIN_TOTAL
        loan_config = {"bufferPercent": 10, "minTotal": SilpoMockServer.BNPL_MIN_TOTAL, "paymentCount": 3}
        loan = {"loanAvailable": bnpl_available, "loanCalculation": None, "loanConfig": loan_config}
        types = [
            {
                "type": name,
                "available": True if name != "BNPL" else bnpl_available,
                "loan": dict(loan) if name == "BNPL" else None,
            }
            for name in SilpoMockServer.PAYMENT_TYPES
        ]
        return {"type": "Unknown", "types": types, "loan": loan}

    def _recompute_totals(self, cart: dict[str, Any]) -> None:
        items_price = sum(item["totalPrice"] for item in cart["items"])
        bonus_applied = min(cart["loyalty"].get("bonusApplied", 0.0), items_price)
        cart["loyalty"]["bonusApplied"] = round(bonus_applied, 2)
        cart["totals"]["itemsPrice"] = round(items_price, 2)
        cart["totals"]["deliveryPrice"] = 0.0
        cart["totals"]["totalPrice"] = round(items_price - bonus_applied, 2)
        cart["totals"]["discount"] = round(sum(item.get("discount", 0.0) for item in cart["items"]), 2)
        self._build_calculation(cart)

    def _build_calculation(self, cart: dict[str, Any]) -> None:
        """Mirror the live ``calculation`` block (release-1.111.3).

        Carries the payment method list with availability, the delivery cost
        split (``subTotal`` flat cost, ``subDiscount`` how much was waived) and
        ``totalAfterDiscounts`` — the amount the guest actually pays.
        """
        totals = cart.get("totals") or {}
        products_total = float(totals.get("itemsPrice") or 0.0)
        bonus_applied = float((cart.get("loyalty") or {}).get("bonusApplied") or 0.0)
        total = round(products_total + float(totals.get("deliveryPrice") or 0.0) - bonus_applied, 2)
        delivery_sub_total = 0.0
        delivery_discount = 0.0
        service_fee = float(cart.get("serviceFee") or 0.0)
        total_after = round(total, 2)
        cart["calculation"] = {
            "total": total,
            "totalAfterDiscounts": total_after,
            "certificatesTotal": 0.0,
            "productsTotal": products_total,
            "subTotal": products_total,
            "subDiscount": bonus_applied,
            "serviceFee": {"total": service_fee, "subTotal": service_fee, "subDiscount": 0.0},
            "delivery": {
                "total": round(delivery_sub_total - delivery_discount, 2),
                "subTotal": delivery_sub_total,
                "subDiscount": delivery_discount,
                "totalWeight": round(sum(item.get("quantity", 0.0) for item in cart["items"]), 3),
                "deliveryExpressByPromise": None,
            },
            "promoCode": cart.get("promoCode"),
            "payment": self._payment_block(total),
            "loyalty": cart.get("loyalty"),
            "validations": self._cart_validations(total),
        }
        cart.setdefault("paymentType", "Unknown")

    @staticmethod
    def _cart_validations(total: float) -> list[dict[str, Any]]:
        """Checkout validations, including the release-1.111.3 payment notice."""
        validations: list[dict[str, Any]] = []
        if total < SilpoMockServer.BNPL_MIN_TOTAL:
            validations.append(
                {
                    "level": "info",
                    "type": "order",
                    "message": "order.payment_types.disabled",
                    "context": {
                        "reason": "not_available_for_total",
                        "paymentTypes": ["BNPL"],
                        "total": total,
                        "minTotal": SilpoMockServer.BNPL_MIN_TOTAL,
                    },
                }
            )
        return validations

    @staticmethod
    def _find_product(productId: str) -> dict[str, Any] | None:
        return next((p for p in PRODUCTS if p["productId"] == productId), None)

    # -- tool registration --------------------------------------------------

    def _register_tools(self) -> None:
        self._register_location_tools()
        self._register_search_tools()
        self._register_catalog_tools()
        self._register_cart_tools()
        self._register_order_tools()
        self._register_profile_tools()
        self._register_loyalty_tools()

    # Location & delivery (6)
    def _register_location_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_find_address(address: str) -> dict[str, Any]:
            """Find coordinates (lat/lng) for an address string.

            Mirrors server release-1.111.1: an unmatched house number is
            flagged via ``warning``/``houseNumberMatched`` instead of a
            silent ``success: true``.
            """
            base = dict(FIXTURE_ADDRESSES[0])
            fixture_house = str(base.get("houseNumber") or "")
            house_tokens = re.findall(r"\d+[A-Za-zА-Яа-яЁёЇїІіЄєҐґ]*", address)
            matched = bool(fixture_house) and fixture_house in house_tokens
            if matched:
                return {
                    "success": True,
                    "summary": "Found 1 address",
                    "addresses": [{**base, "houseNumberMatched": True, "warning": None}],
                }
            return {
                "success": True,
                "summary": "Found 1 address with warnings: house number could not be matched",
                "addresses": [
                    {
                        **base,
                        "houseNumberMatched": False,
                        "warning": (
                            "House number could not be matched for "
                            f"'{address}'; coordinates are for the street, not the house."
                        ),
                    }
                ],
                "warning": "House number could not be matched; coordinates are approximate.",
            }

        @self._fastmcp.tool
        def silpo_get_available_delivery_types(
            latitude: float,
            longitude: float,
        ) -> list[dict[str, Any]]:
            """Return available delivery types for coordinates.

            Mirrors server release-1.111.1 docs: coordinates are only
            validated for home-delivery types — SelfPickup/NovaPoshta options
            are returned regardless of the coordinate.
            """
            _ = (latitude, longitude)
            return [
                {
                    "type": "DeliveryHome",
                    "deliveryType": "DeliveryHome",
                    "branchId": "bran-1",
                    "description": "Доставка додому",
                    "minOrder": 400.0,
                },
                {
                    "type": "SelfPickup",
                    "deliveryType": "SelfPickup",
                    "branchId": "bran-1",
                    "description": "Самовивіз",
                    "minOrder": 0.0,
                },
            ]

        @self._fastmcp.tool
        def silpo_list_branches(
            limit: int | None = None,
            offset: int | None = None,
            hasPickup: bool | None = None,
            hasNP: bool | None = None,
        ) -> list[dict[str, Any]]:
            """List Silpo branches, optionally filtered."""
            _ = (limit, offset)
            result = list(BRANCHES)
            if hasPickup is not None:
                result = [b for b in result if b["hasPickup"] == hasPickup]
            if hasNP is not None:
                result = [b for b in result if b["hasNovaPoshta"] == hasNP]
            if limit is not None:
                result = result[:limit]
            return result

        @self._fastmcp.tool
        def silpo_get_time_slots(
            branchId: str,
            deliveryTypes: list[str] | None = None,
            deliveryType: str | None = None,
            limit: int | None = None,
            start: str | None = None,
            end: str | None = None,
        ) -> list[dict[str, Any]]:
            """Return available delivery time slots for a branch.

            Mirrors server release-1.111.0 (no duplicate slots; singular
            ``deliveryType`` accepted as an alias for ``deliveryTypes``),
            release-1.111.1 (millisecond timestamps accepted; each slot
            carries ``serviceFee`` — the SelfPickup "Сервісний збір" fee) and
            release-1.111.2 (timeslot bounds are normalized — ``Z``,
            ``+00:00`` and naive stamps are read as UTC, date-only values are
            rejected; ``deliveryTypes`` is restricted to the 9-value enum and
            ``limit`` must be between 1 and 100).

            Release-1.111.3 clarified the semantics: ``available`` is
            authoritative (a type can show pricing while every slot is
            unavailable), ``minOrderCost`` is reported only here, ``serviceFee``
            is a preview that ``cart.calculation.serviceFee.total`` supersedes,
            and all slot times are UTC.

            Release-1.111.4 made the date normalizer more lenient
            (whitespace, lowercase ``z``, comma fractions, ``+HHMM``/``+HH``
            offsets and a space separator are read as UTC) and added a
            ``total`` to the live response (``{success, summary, slots,
            total}``); the mock keeps returning the bare slot list, which the
            typed client unwraps from either shape.
            """
            if limit is not None and not 1 <= limit <= 100:
                raise ValueError(f"limit must be between 1 and 100, got {limit}")
            types = deliveryTypes or ([deliveryType] if deliveryType else [])
            accepted = [member.value for member in TimeSlotDeliveryType]
            invalid = [t for t in types if t not in accepted]
            if invalid:
                raise ValueError(
                    f"Invalid option for deliveryTypes: expected one of {'|'.join(accepted)}; got {invalid}"
                )
            dtype = types[0] if types else "SelfPickup"
            service_fee = 15.0 if dtype == "SelfPickup" else 0.0
            start_at = _parse_slot_bound(start, "start") if start is not None else None
            end_at = _parse_slot_bound(end, "end") if end is not None else None
            slots = [
                {
                    "id": f"slot-{i}",
                    "deliveryType": dtype,
                    "branchId": branchId,
                    "startsAt": f"2026-09-02T{i + 8:02d}:00:00+00:00",
                    "endsAt": f"2026-09-02T{i + 10:02d}:00:00+00:00",
                    "start": f"2026-09-02T{i + 8:02d}:00:00+00:00",
                    "end": f"2026-09-02T{i + 10:02d}:00:00+00:00",
                    "price": 0.0 if i == 0 else 45.0,
                    "deliveryCost": 0.0 if i == 0 else 45.0,
                    "deliveryCostMap": [
                        {"cost": 0.0 if i == 0 else 45.0, "fromOrderCost": 199.0},
                    ],
                    "minOrderCost": 199.0,
                    "maxWeight": None,
                    "constraints": {
                        "isLimitedAlcohol": False,
                        "isLimitedTobacco": False,
                        "isLimitedCookedFood": False,
                        "isLimitedOwnCooking": False,
                    },
                    "fast": {"cost": 0.0, "time": 30} if i == 0 else None,
                    "isAvailable": True,
                    "available": True,
                    "isExpress": i == 0,
                    "serviceFee": service_fee,
                }
                for i in range(3)
            ]
            if start_at is not None:
                slots = [s for s in slots if datetime.fromisoformat(s["start"]) >= start_at]
            if end_at is not None:
                slots = [s for s in slots if datetime.fromisoformat(s["start"]) < end_at]
            return slots[:limit] if limit is not None else slots

        @self._fastmcp.tool
        def silpo_find_nova_poshta_settlements(title: str) -> list[dict[str, Any]]:
            """Find Nova Poshta settlements by name."""
            q = title.lower()
            return [s for s in NOVA_POSHTA_SETTLEMENTS if q in str(s["name"]).lower()]

        @self._fastmcp.tool
        def silpo_find_nova_poshta_offices(
            settlementId: str,
            title: str | None = None,
        ) -> list[dict[str, Any]]:
            """Find Nova Poshta offices/postomats in a settlement."""
            _ = title
            return NOVA_POSHTA_OFFICES

    # Product search (7)
    def _register_search_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_find_products_batch(
            branchId: str,
            deliveryType: str,
            timeslotStart: str,
            timeslotEnd: str,
            products: list[str],
            limit: int | None = None,
        ) -> dict[str, Any]:
            """Search up to 30 products in parallel by list of shopping items."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd)
            dropped = sum(1 for q in products if not q.strip())
            valid = [q for q in products if q.strip()]
            queries: list[dict[str, Any]] = []
            total_products = 0
            for query in valid:
                lim = limit or 1
                stripped = query.strip()
                matches = [
                    p
                    for p in PRODUCTS
                    if stripped.lower() in p["title"].lower()
                    or stripped.lower() in p["category"].lower()
                    or stripped == str(p.get("externalProductId"))
                ]
                total_found = len(matches)
                chosen = matches[:lim]
                total_products += len(chosen)
                queries.append({"query": query, "totalFound": total_found, "products": chosen})
            if dropped:
                summary = (
                    f"Found {total_products} products across {len(queries)} search queries "
                    f"({dropped} empty/whitespace-only entries skipped)"
                    if queries
                    else f"No valid product names provided — all {dropped} entry was empty or whitespace-only"
                    if dropped == 1
                    else f"No valid product names provided — all {dropped} entries were empty or whitespace-only"
                )
            elif not queries:
                summary = "No products specified."
            else:
                summary = f"Found {total_products} products across {len(queries)} search queries"
            return {
                "success": True,
                "summary": summary,
                "queries": queries,
                "meta": {
                    "totalQueries": len(queries),
                    "totalProducts": total_products,
                    "droppedCount": dropped,
                },
            }

        @self._fastmcp.tool
        def silpo_get_products(
            branchId: str,
            deliveryType: str,
            timeslotStart: str,
            timeslotEnd: str,
            mustHavePromotion: bool | None = None,
            category: str | None = None,
            promotionCode: str | None = None,
            inStock: bool | None = None,
            set: str | None = None,
            limit: int | None = None,
            offset: int | None = None,
            sortBy: str | None = None,
            sortDirection: str | None = None,
            fromPrice: float | None = None,
            toPrice: float | None = None,
        ) -> dict[str, Any]:
            """Products with filters: category, promotion, stock, pagination.

            Mirrors server release-1.111.0: at least one of category /
            mustHavePromotion / promotionCode / set is required (clear message
            instead of a raw 400). Timeslots are not validated against real
            delivery windows — a nonexistent slot returns the full catalog.
            """
            _ = (deliveryType, timeslotStart, timeslotEnd, promotionCode, set, sortBy, sortDirection)
            if category is None and mustHavePromotion is None and promotionCode is None and set is None:
                raise ValueError("At least one filter is required: category, mustHavePromotion, promotionCode, set")
            page = 1
            pageSize = limit or 20
            if offset is not None:
                page = offset // pageSize + 1
            items = list(PRODUCTS)
            if category:
                cat = next((c for c in CATEGORIES if c["slug"] == category or c["title"] == category), None)
                if cat:
                    items = [p for p in items if p["category"] == cat["title"]]
            if inStock is not None:
                items = [p for p in items if p["isAvailable"] == inStock]
            if mustHavePromotion is not None:
                items = [p for p in items if p["isOnSale"] == mustHavePromotion]
            if fromPrice is not None:
                items = [p for p in items if float(p.get("displayPrice") or p["price"]) >= fromPrice]
            if toPrice is not None:
                items = [p for p in items if float(p.get("displayPrice") or p["price"]) <= toPrice]
            start = (page - 1) * pageSize
            return {
                "items": items[start : start + pageSize],
                "total": len(items),
                "page": page,
                "pageSize": pageSize,
                "hasMore": start + pageSize < len(items),
            }

        @self._fastmcp.tool
        def silpo_get_product_details(
            branchId: str,
            slug: str,
            deliveryType: str,
            timeslotStart: str,
            timeslotEnd: str,
        ) -> dict[str, Any]:
            """Full product card: branch-real price/stock plus hasOfferAtBranch.

            Mirrors server release-1.110.0: pricing reflects the requested
            branch's real offer, and ``hasOfferAtBranch`` is False when the
            product has no offer at that branch (then ``stock`` is 0 and
            ``available`` is False; ``price``/``displayPrice`` fall back to
            the catalog values for reference).
            """
            _ = (deliveryType, timeslotStart, timeslotEnd)
            product = next((p for p in PRODUCTS if p["slug"] == slug), None)
            if product is None:
                raise ValueError(f"Product not found: {slug}")
            has_offer = product["branchId"] == branchId
            return {
                "id": product["productId"],
                "name": product["title"],
                "slug": product["slug"],
                "price": product["price"],
                "displayPrice": product.get("displayPrice", product["price"]),
                "oldPrice": product["oldPrice"],
                "stock": product.get("stock", 10.0) if has_offer else 0.0,
                "available": product["isAvailable"] if has_offer else False,
                "hasOfferAtBranch": has_offer,
                "image": product.get("imageUrl"),
                "weighted": product.get("weighted", False),
                "step": product.get("step", 1.0),
                "ratio": product.get("unit", "шт"),
                "displayRatio": product.get("displayRatio"),
                "specialPrices": product.get("specialPrices"),
                "companyId": product["companyId"],
                "branchId": branchId,
                "externalProductId": product.get("externalProductId"),
                "url": f"https://silpo.ua/product/{product['slug']}",
                "images": [product["imageUrl"]],
                "attributes": {"brand": product["brand"]},
            }

        @self._fastmcp.tool
        def silpo_get_similar_products(
            branchId: str,
            slug: str,
            deliveryType: str,
            timeslotStart: str,
            timeslotEnd: str,
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """Similar/alternative products by slug."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit, offset)
            source = next((p for p in PRODUCTS if p["slug"] == slug), None)
            if source is None:
                return []
            res = [p for p in PRODUCTS if p is not source][:2]
            if limit is not None:
                res = res[:limit]
            return res

        @self._fastmcp.tool
        def silpo_get_replacements(
            branchId: str,
            companyId: str,
            productIds: list[str],
            deliveryType: str,
        ) -> dict[str, Any]:
            """Replacements for out-of-stock products."""
            _ = (branchId, companyId, deliveryType)
            items: list[dict[str, Any]] = []
            for productId in productIds:
                product = self._find_product(productId)
                if product and not product["isAvailable"]:
                    alt = next(
                        (p for p in PRODUCTS if p["isAvailable"] and p["category"] == product["category"]),
                        None,
                    )
                    items.append({"productId": productId, "replacements": [alt] if alt else []})
                else:
                    items.append({"productId": productId, "replacements": []})
            return {"success": True, "summary": f"Checked {len(items)} products", "items": items}

        @self._fastmcp.tool
        def silpo_get_my_favorites(
            branchId: str,
            deliveryType: str,
            timeslotStart: str,
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """List the guest's favorite products."""
            _ = (branchId, deliveryType, timeslotStart, limit, offset)
            return [p for p in PRODUCTS if p["productId"] in self._favorites]

        @self._fastmcp.tool
        def silpo_add_or_update_favorite_products(
            actions: list[dict[str, Any]],
        ) -> dict[str, Any]:
            """Add or remove products to/from favorites."""
            for act in actions:
                pid = act.get("productId")
                to_delete = act.get("toDelete", False)
                if pid is None:
                    continue
                if not to_delete:
                    if pid not in self._favorites:
                        self._favorites.append(pid)
                else:
                    if pid in self._favorites:
                        self._favorites.remove(pid)
            return {
                "success": True,
                "summary": f"Favorites updated ({len(self._favorites)} total)",
                "actions": actions,
            }

    # Catalog (6)
    def _register_catalog_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_promotions(
            branchId: str,
            deliveryType: str,
            timeslotStart: str,
            timeslotEnd: str,
        ) -> list[dict[str, Any]]:
            """Active promotions and discounts.

            Mirrors server release-1.111.4: an unknown branch returns an
            empty list instead of the previous ``500`` error.
            """
            _ = (deliveryType, timeslotStart, timeslotEnd)
            if branchId not in {branch["branchId"] for branch in BRANCHES}:
                return []
            return PROMOTIONS

        @self._fastmcp.tool
        def silpo_get_popular_categories(
            branchId: str,
            deliveryType: str,
        ) -> list[dict[str, Any]]:
            """Popular categories in the branch."""
            _ = (branchId, deliveryType)
            return CATEGORIES[:3]

        @self._fastmcp.tool
        def silpo_get_category(
            branchId: str,
            deliveryType: str,
            categorySlug: str,
        ) -> dict[str, Any]:
            """Details of a category: breadcrumb path and price range.

            Mirrors server release-1.111.3: the tool no longer returns child
            categories — the upstream API never includes them for this
            endpoint. Use silpo_get_categories_tree to discover children.
            """
            _ = (branchId, deliveryType)
            category = next((c for c in CATEGORIES if c["slug"] == categorySlug), None)
            if category is None:
                raise ValueError(f"Category not found: {categorySlug}")
            path: list[dict[str, Any]] = []
            cursor: dict[str, Any] | None = category
            while cursor is not None:
                path.append({"id": cursor["id"], "slug": cursor["slug"], "title": cursor["title"]})
                parent_id = cursor.get("parentId")
                cursor = next((c for c in CATEGORIES if c["id"] == parent_id), None) if parent_id else None
            path.reverse()
            return {
                "success": True,
                "category": {
                    **category,
                    "path": path,
                    "priceRange": {"min": 12.5, "max": 249.9},
                    "visible": True,
                },
            }

        @self._fastmcp.tool
        def silpo_get_categories(
            branchId: str,
            parentId: str | None = None,
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """Flat list of all categories."""
            _ = (parentId, limit, offset)
            return CATEGORIES

        @self._fastmcp.tool
        def silpo_get_categories_tree(
            branchId: str,
            deliveryType: str,
            timeslotStart: str,
            timeslotEnd: str,
        ) -> dict[str, Any]:
            """Full category tree."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd)
            roots = [c for c in CATEGORIES if c["parentId"] is None]
            tree = []
            for root in roots:
                tree.append({**root, "children": [c for c in CATEGORIES if c["parentId"] == root["id"]]})
            return {"rootCategories": tree}

        @self._fastmcp.tool
        def silpo_get_product_sets(
            branchId: str,
            deliveryType: str | None = None,
        ) -> list[dict[str, Any]]:
            """Curated product sets."""
            _ = (branchId, deliveryType)
            return PRODUCT_SETS

    # Cart (8)
    def _register_cart_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_my_shopping_cart(context: Context) -> dict[str, Any]:
            """Return the ID of the active cart."""
            cart_id = self._ensure_cart(self._session_key(context))
            return {"success": True, "cartId": cart_id, "shoppingCartId": cart_id, "exists": True}

        @self._fastmcp.tool
        def silpo_create_shopping_cart(
            context: Context,
            addressType: str,
            latitude: float | str,
            longitude: float | str,
            deliveryType: str,
            branchId: str,
            timeslot: dict[str, Any],
            city: str | None = None,
            street: str | None = None,
            house: str | None = None,
            district: str | None = None,
        ) -> dict[str, Any]:
            """Create a cart; idempotent — returns the existing cart when present."""
            session_key = self._session_key(context)
            if session_key is not None:
                existing_id = SilpoMockServer._mock_carts.get(session_key)
                if existing_id is not None and existing_id in self._carts:
                    return {
                        "success": True,
                        "summary": "Shopping cart already exists",
                        "shoppingCartId": existing_id,
                    }
            slot = timeslot
            cart_id = f"cart-{uuid.uuid4().hex[:8]}"
            self._carts[cart_id] = self._new_cart(
                cart_id,
                deliveryType,
                {
                    "addressType": addressType,
                    "latitude": str(latitude),
                    "longitude": str(longitude),
                    "city": city,
                    "street": street,
                    "house": house,
                    "district": district,
                },
                [{"companyId": "co-1", "branchId": branchId}],
            )
            self._carts[cart_id]["timeslot"] = slot
            if session_key is not None:
                SilpoMockServer._mock_carts[session_key] = cart_id
            return {
                "success": True,
                "summary": "Shopping cart created",
                "shoppingCartId": cart_id,
            }

        @self._fastmcp.tool
        def silpo_get_shopping_cart_by_id(shoppingCartId: str) -> dict[str, Any]:
            """Return the full cart: items, delivery, slot, sums, validations.

            Mirrors server release-1.111.1 (``serviceFee`` — the SelfPickup
            "Сервісний збір" fee) and release-1.111.3 (``calculation.payment``
            lists every payment method with its availability, plus the delivery
            discount split and ``totalAfterDiscounts``).
            """
            if shoppingCartId not in self._carts:
                raise ValueError(f"Cart not found: {shoppingCartId}")
            cart = self._carts[shoppingCartId]
            cart.setdefault("serviceFee", self._service_fee_for(str(cart.get("deliveryType") or "")))
            totals = cart.get("totals")
            if isinstance(totals, dict):
                totals.setdefault("serviceFee", cart["serviceFee"])
            self._build_calculation(cart)
            return cart

        @self._fastmcp.tool
        def silpo_add_or_update_cart_products(
            shoppingCartId: str,
            products: list[dict[str, Any]],
        ) -> dict[str, Any]:
            """Add products or update quantities in the cart.

            ``products`` entries carry ``productId`` + ``companyId`` +
            ``branchId`` plus ``quantity`` (kilograms for weighted products);
            omitted/false ``addQuantity`` replaces the line quantity while
            ``true`` adds to it, and ``comment`` holds per-line instructions.
            Clarified in release-1.111.4; behavior is unchanged.
            """
            cid = shoppingCartId
            if cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            for incoming in products:
                product = self._find_product(incoming["productId"])
                if product is None:
                    raise ValueError(f"Product not found: {incoming['productId']}")
                quantity = float(incoming.get("quantity", 1))
                existing = next((i for i in cart["items"] if i["productId"] == product["productId"]), None)
                if existing is not None:
                    if incoming.get("addQuantity"):
                        quantity = float(existing.get("quantity", 0.0)) + quantity
                    cart["items"].remove(existing)
                line = {
                    "productId": product["productId"],
                    "companyId": product["companyId"],
                    "branchId": product["branchId"],
                    "title": product["title"],
                    "quantity": quantity,
                    "unitPrice": product["price"],
                    "totalPrice": round(product["price"] * quantity, 2),
                    "isAvailable": product["isAvailable"],
                }
                if incoming.get("comment") is not None:
                    line["comment"] = incoming["comment"]
                cart["items"].append(line)
            self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_remove_cart_products(
            shoppingCartId: str,
            products: list[dict[str, Any]],
        ) -> dict[str, Any]:
            """Remove specific products from the cart."""
            cid = shoppingCartId
            if cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            ids = {str(p.get("productId") or p.get("id")) for p in products if p.get("productId") or p.get("id")}
            cart["items"] = [i for i in cart["items"] if i["productId"] not in ids]
            self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_clear_shopping_cart(shoppingCartId: str) -> dict[str, Any]:
            """Clear the entire cart."""
            if shoppingCartId not in self._carts:
                raise ValueError(f"Cart not found: {shoppingCartId}")
            cart = self._carts[shoppingCartId]
            cart["items"] = list[dict[str, Any]]()
            cart["loyalty"]["bonusRequested"] = None
            cart["loyalty"]["bonusApplied"] = 0.0
            self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_update_shopping_cart(
            shoppingCartId: str,
            deliveryType: str,
            timeslot: dict[str, Any],
            address: dict[str, Any],
            shipments: list[dict[str, Any]],
            branchId: str | None = None,
            feedbackChanges: str | None = None,
            feedbackContacts: str | None = None,
            isAdultConfirmed: bool | None = None,
            promoCode: str | None = None,
            bonusRequested: float | None = None,
        ) -> dict[str, Any]:
            """Update delivery, slot, address, shipments, or apply bonuses.

            Mirrors the release-1.111.3 schema: ``address`` must carry an
            ``addressType``, every shipment a ``companyId``/``branchId`` pair
            (both are copied verbatim from the cart, not constructed), and
            ``deliveryType`` is limited to the eight schedulable types.

            ``bonusRequested`` is nullable as in the live schema, but a mock
            tool function cannot distinguish an explicit ``null`` from an
            omitted argument — so ``null`` leaves the request untouched here.
            """
            cid = shoppingCartId
            if cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            invalid_type = next((t for t in _UPDATE_CART_DELIVERY_TYPES if t == deliveryType), None)
            if invalid_type is None:
                raise ValueError(
                    f"Invalid option for deliveryType: expected one of "
                    f"{'|'.join(_UPDATE_CART_DELIVERY_TYPES)}; got {deliveryType!r}"
                )
            if not isinstance(address, dict) or not address.get("addressType"):
                raise ValueError(
                    "address.addressType is required (release-1.111.3); copy the address "
                    "object from silpo_get_shopping_cart_by_id"
                )
            if not shipments:
                raise ValueError("shipments must contain at least one entry (release-1.111.3)")
            for index, shipment in enumerate(shipments):
                missing = [
                    k for k in ("companyId", "branchId") if not isinstance(shipment, dict) or not shipment.get(k)
                ]
                if missing:
                    raise ValueError(
                        f"shipments[{index}] is missing {' and '.join(missing)} (release-1.111.3); "
                        "copy the shipments array from silpo_get_shopping_cart_by_id"
                    )
            cart = self._carts[cid]
            cart["deliveryType"] = deliveryType
            cart["timeslot"] = timeslot
            cart["address"] = address
            cart["shipments"] = shipments
            if not branchId and shipments and isinstance(shipments[0], dict):
                branchId = shipments[0].get("branchId")
            fee = self._service_fee_for(deliveryType)
            cart["serviceFee"] = fee
            if isinstance(cart.get("totals"), dict):
                cart["totals"]["serviceFee"] = fee
            if branchId is not None:
                cart["branchId"] = branchId
            if promoCode is not None:
                cart["promoCode"] = promoCode
            _ = (feedbackChanges, feedbackContacts, isAdultConfirmed)
            if bonusRequested is not None:
                available = cart["loyalty"].get("bonusAvailable", 0.0)
                cart["loyalty"]["bonusRequested"] = min(bonusRequested, available)
                cart["loyalty"]["bonusApplied"] = cart["loyalty"]["bonusRequested"]
            self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_add_or_update_certificates(
            shoppingCartId: str,
            certificatesToAdd: list[Any] | None = None,
            certificatesToRemove: list[Any] | None = None,
        ) -> dict[str, Any]:
            """Add or remove gift certificates from the cart."""
            if shoppingCartId not in self._carts:
                raise ValueError(f"Cart not found: {shoppingCartId}")
            cart = self._carts[shoppingCartId]
            _ = certificatesToRemove

            def _barcode(cert: Any) -> str:
                return cert.get("barcode", "") if isinstance(cert, dict) else str(cert)

            added = [_barcode(c) for c in (certificatesToAdd or [])]
            cart["certificates"] = added
            return {
                "success": True,
                "summary": f"Added {len(added)} certificates",
                "added": [{"barcode": b, "faceValue": None, "validations": []} for b in added],
                "removed": [],
            }

    # Orders (2)
    def _register_order_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_my_online_orders(
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """History of online orders."""
            _ = (limit, offset)
            return [
                {
                    "orderId": "ord-1",
                    "number": "1001",
                    "createdAt": "2026-07-15T10:30:00Z",
                    "status": "delivered",
                    "amount": 245.5,
                    "discount": 12.0,
                    "delivery": {
                        "type": "DeliveryHome",
                        "timeSlot": {"from": "2026-07-15T10:00:00Z", "to": "2026-07-15T11:00:00Z"},
                        "deliveredAt": "2026-07-15T10:45:00Z",
                    },
                    "address": {
                        "city": "Київ",
                        "street": "вул. Анни Ахматової",
                        "building": "9",
                        "apartment": "19",
                    },
                    "products": [
                        {
                            "id": "prd-milk-2pct",
                            "name": "Молоко Премія 2.5% 900 мл",
                            "price": 36.9,
                            "quantity": 2,
                            "subtotal": 73.8,
                            "removed": False,
                            "image": "https://images.silpo.ua/mock/milk.png",
                            "companyId": "co-1",
                            "branchId": "bran-1",
                        }
                    ],
                }
            ]

        @self._fastmcp.tool
        def silpo_get_my_offline_orders(
            branchId: str,
            deliveryType: str,
            timeslotStart: str,
            timeslotEnd: str,
            limit: int | None = None,
            offset: int | None = None,
            dateStart: str | None = None,
            dateEnd: str | None = None,
        ) -> list[dict[str, Any]]:
            """History of physical-store purchases: receipts."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit, offset, dateStart, dateEnd)
            return [
                {
                    "filId": 1998,
                    "filialName": "Сільпо Львів (центр)",
                    "cityName": "Львів",
                    "createdAt": "2026-07-01T18:15:00Z",
                    "sumReg": 180.0,
                    "accruedBalaBonusesSum": 3.6,
                    "sumDiscount": 12.0,
                    "receiptUrl": "https://silpo.ua/receipt/rec-1",
                    "chequeMagicName": None,
                    "chequePrediction": None,
                    "rewards": [],
                    "products": [],
                }
            ]

    # Profile (4)
    def _register_profile_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_my_profile() -> dict[str, Any]:
            """Profile data: name, phone, email, birth date."""
            return {
                "id": "profile-1",
                "firstName": "Олексій",
                "lastName": "Овдієнко",
                "middleName": None,
                "phone": "+380501112233",
                "email": "oleksii@example.com",
                "birthday": None,
                "gender": None,
                "status": "active",
            }

        @self._fastmcp.tool
        def silpo_get_my_delivery_addresses() -> list[dict[str, Any]]:
            """Saved delivery addresses."""
            return [
                {
                    "id": "addr-1",
                    "tag": "Дім",
                    "city": "Київ",
                    "street": "вул. Анни Ахматової",
                    "building": "9",
                    "apartment": "19",
                    "floor": None,
                    "entrance": None,
                    "latitude": 50.3957,
                    "longitude": 30.6217,
                    "comment": None,
                }
            ]

        @self._fastmcp.tool
        def silpo_get_my_family() -> list[dict[str, Any]]:
            """Family members in the profile."""
            return [
                {
                    "profileId": "member-1",
                    "name": "Софія",
                    "phone": "+380501112234",
                    "image": None,
                    "profileCreatedAt": "2026-01-01T00:00:00Z",
                    "itsMe": False,
                },
                {
                    "profileId": "member-me",
                    "name": "Олексій",
                    "phone": "+380501112233",
                    "image": None,
                    "profileCreatedAt": "2025-01-01T00:00:00Z",
                    "itsMe": True,
                },
            ]

        @self._fastmcp.tool
        def silpo_get_my_food_restrictions() -> dict[str, Any]:
            """Dietary restrictions and food preferences."""
            return {
                "restrictions": [{"slug": "lactose-free", "name": "безлактозна дієта"}],
                "preferences": ["органічні продукти"],
            }

    # Loyalty & promotions (7)
    def _register_loyalty_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_loyalty_info() -> dict[str, Any]:
            """Vlasnyi Rakunok loyalty card info."""
            return {
                "cardNumber": "6000000000000000",
                "status": "sribnyi",
                "bonusBalance": 125.5,
                "bonusEarned": 8.4,
            }

        @self._fastmcp.tool
        def silpo_get_my_coupons() -> list[dict[str, Any]]:
            """Available discount coupons."""
            return [
                {
                    "id": 520703581,
                    "active": True,
                    "useWay": "Електронний",
                    "beginDate": "2026-09-01",
                    "endDate": "2026-09-30",
                    "endDateTime": "2026-09-30T23:59:59",
                    "description": "Знижка 50 грн від 500 грн",
                    "limitText": "Мінімальне замовлення 500 грн",
                    "warningText": "Один купон на замовлення",
                    "image": "https://images.silpo.ua/mock/coupon.png",
                    "promoId": 304950,
                    "rewardText": "-50₴",
                    "rewardValue": 50.0,
                    "rewardUnit": "₴",
                    "rewardSign": "-",
                    "rewardLimit": 50.0,
                }
            ]

        @self._fastmcp.tool
        def silpo_get_coupon_details(businessCouponId: int | float | str) -> dict[str, Any]:
            """Full coupon info: eligibility, conditions, reward, progress.

            Release-1.111.5: gateway coupons carry ``successorThreshold``.
            The ``Yezzz!`` fixture id (600971427) returns the live gateway
            shape; any other id returns the ordinary coupon.
            """
            try:
                coupon_key = int(float(str(businessCouponId)))
            except (TypeError, ValueError):
                coupon_key = None
            if coupon_key == 600971427:
                return {
                    "id": 600971427,
                    "active": True,
                    "state": "Активний",
                    "canBeAppliedToOrder": True,
                    "useWay": "Електронний",
                    "beginDate": "2026-09-22",
                    "endDate": "2026-10-22",
                    "endDateTime": "2026-10-22T23:59:59",
                    "usedCount": 0,
                    "description": "Безкоштовний мобільний зв’язок Yezzz!",
                    "limitText": "Акція діє на всі товари Сільпо",
                    "warningText": "За придбання товарів в «Сільпо» на суму 2000 грн",
                    "rewardText": "",
                    "rewardValue": None,
                    "image": "https://images.silpo.ua/mock/coupon.png",
                    "promoId": 257654,
                    "rewardUnit": None,
                    "rewardSign": None,
                    "rewardLimit": None,
                    "progress": {"current": 0.0, "target": 2000.0, "percent": 0.0, "unit": "₴"},
                    "successorThreshold": {
                        "promoId": 257655,
                        "amount": 2000.0,
                        "description": "безкоштовний зв'язок",
                        "rewardText": "-",
                    },
                }
            _ = businessCouponId  # mock returns the fixture coupon for any other id
            return {
                "id": 520703581,
                "active": True,
                "state": "Активний",
                "canBeAppliedToOrder": True,
                "useWay": "Електронний",
                "beginDate": "2026-09-01",
                "endDate": "2026-09-30",
                "endDateTime": "2026-09-30T23:59:59",
                "usedCount": 0,
                "description": "Знижка 50 грн від 500 грн",
                "limitText": "Мінімальне замовлення 500 грн",
                "warningText": "Один купон на замовлення",
                "rewardText": "-50₴",
                "rewardValue": 50.0,
                "image": "https://images.silpo.ua/mock/coupon.png",
                "promoId": 304950,
                "rewardUnit": "₴",
                "rewardSign": "-",
                "rewardLimit": 50.0,
                "progress": None,
                "successorThreshold": None,
            }

        @self._fastmcp.tool
        def silpo_get_my_promos() -> list[dict[str, Any]]:
            """Personal promo offers."""
            return [
                {
                    "promoId": 257654,
                    "selected": True,
                    "beginDate": "2026-08-01",
                    "endDate": "2026-09-01",
                    "description": "Особиста пропозиція на сир.",
                    "rewardText": "-15%",
                    "rewardValue": 15.0,
                    "limitText": "Діє на сир Гауда",
                    "warningText": None,
                    "addressListText": None,
                    "image": "https://images.silpo.ua/mock/promo.png",
                }
            ]

        @self._fastmcp.tool
        def silpo_get_promo_codes() -> list[dict[str, Any]]:
            """Active promo codes."""
            return [
                {
                    "id": "promo-code-1",
                    "code": "SUMMER2026",
                    "title": "Знижка 5% на перше замовлення",
                    "active": True,
                }
            ]

        @self._fastmcp.tool
        def silpo_get_my_certificates(
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """Active gift certificates."""
            _ = (limit, offset)
            return [
                {
                    "id": 1,
                    "createdAt": "2026-01-01T00:00:00",
                    "totalPrice": 200.0,
                    "barcode": "4820000000002",
                    "pincode": None,
                    "expireDate": "2026-12-31",
                    "title": "Подарунковий сертифікат 200 грн",
                    "image": "https://images.silpo.ua/mock/cert.png",
                }
            ]

        @self._fastmcp.tool
        def silpo_get_my_premium_subscription() -> dict[str, Any]:
            """Silpo Premium subscription status."""
            return {
                "success": True,
                "summary": "Active premium subscription",
                "webLink": "https://silpo.ua/subscription",
                "mobileLink": "https://link.silpo.ua/mock",
                "id": "sub-1",
                "profileId": "profile-1",
                "subscriptionId": "premium-1",
                "createdAt": "2026-01-01T00:00:00Z",
                "status": "active",
                "dateFrom": "2026-01-01T00:00:00Z",
                "dateTo": "2026-11-30T23:59:59Z",
                "features": [],
                "bonusesObtainedAmount": 10.0,
                "shareWebLink": "https://silpo.ua/subscription/share",
                "shareMobileLink": "https://link.silpo.ua/mock-share",
            }
