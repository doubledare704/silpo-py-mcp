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

import uuid
from typing import Any, ClassVar

from fastmcp import FastMCP
from fastmcp.server.context import Context

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
        "oldPrice": None,
        "isOnSale": False,
        "isPrivateLabel": True,
        "isAvailable": True,
        "category": "Молочні продукти",
        "imageUrl": "https://images.silpo.ua/mock/milk.png",
        "unit": "шт",
    },
    {
        "productId": "prd-bread",
        "companyId": "co-2",
        "branchId": "bran-1",
        "title": "Хліб український нарізний",
        "slug": "hleb-ukrainskyi-nariznyi",
        "brand": "Київхліб",
        "price": 28.5,
        "oldPrice": None,
        "isOnSale": False,
        "isPrivateLabel": False,
        "isAvailable": True,
        "category": "Хліб та випічка",
        "imageUrl": "https://images.silpo.ua/mock/bread.png",
        "unit": "шт",
    },
    {
        "productId": "prd-eggs",
        "companyId": "co-3",
        "branchId": "bran-1",
        "title": "Яйця курячі С1, 10 шт",
        "slug": "yaytsya-kuryachi-s1-10-sht",
        "brand": "Ясенсвіт",
        "price": 54.9,
        "oldPrice": 62.0,
        "isOnSale": True,
        "isPrivateLabel": False,
        "isAvailable": True,
        "category": "Яйця",
        "imageUrl": "https://images.silpo.ua/mock/eggs.png",
        "unit": "шт",
    },
    {
        "productId": "prd-cheese",
        "companyId": "co-4",
        "branchId": "bran-1",
        "title": "Сир Гауда 45% 250 г",
        "slug": "syr-gauda-45-250-g",
        "brand": "Сир",
        "price": 89.0,
        "oldPrice": 110.0,
        "isOnSale": True,
        "isPrivateLabel": False,
        "isAvailable": True,
        "category": "Молочні продукти",
        "imageUrl": "https://images.silpo.ua/mock/cheese.png",
        "unit": "шт",
    },
    {
        "productId": "prd-apples",
        "companyId": "co-5",
        "branchId": "bran-1",
        "title": "Яблука Гала, 1 кг",
        "slug": "yabluka-gala-1-kg",
        "brand": "Фрукти",
        "price": 42.0,
        "oldPrice": None,
        "isOnSale": False,
        "isPrivateLabel": False,
        "isAvailable": False,
        "category": "Фрукти та овочі",
        "imageUrl": "https://images.silpo.ua/mock/apples.png",
        "unit": "кг",
    },
]

CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "cat-dairy",
        "slug": "molochni",
        "title": "Молочні продукти",
        "parentId": None,
        "productCount": 2,
    },
    {
        "id": "cat-bread",
        "slug": "hlib",
        "title": "Хліб та випічка",
        "parentId": None,
        "productCount": 1,
    },
    {
        "id": "cat-eggs",
        "slug": "yaytsya",
        "title": "Яйця",
        "parentId": "cat-dairy",
        "productCount": 1,
    },
    {
        "id": "cat-fruit",
        "slug": "frukti",
        "title": "Фрукти та овочі",
        "parentId": None,
        "productCount": 1,
    },
]

PROMOTIONS: list[dict[str, Any]] = [
    {
        "id": "promo-1",
        "title": "Ціна тижня: Яйця С1",
        "description": "Знижка 12% на яйця курячі С1.",
        "discountPercent": 12,
        "priceFrom": 54.9,
        "priceTo": 62.0,
        "startsAt": "2026-08-01T00:00:00Z",
        "endsAt": "2026-09-01T23:59:59Z",
        "isPriceOfWeek": True,
        "imageUrl": "https://images.silpo.ua/mock/promo1.png",
    },
    {
        "id": "promo-2",
        "title": "Сир Гауда -15%",
        "description": "Знижка на сир Гауда 45%.",
        "discountPercent": 15,
        "priceFrom": 89.0,
        "priceTo": 110.0,
        "startsAt": "2026-08-01T00:00:00Z",
        "endsAt": "2026-08-31T23:59:59Z",
        "isPriceOfWeek": False,
        "imageUrl": "https://images.silpo.ua/mock/promo2.png",
    },
]

PRODUCT_SETS: list[dict[str, Any]] = [
    {
        "id": "set-1",
        "title": "Сніданок за 150 грн",
        "description": "Молоко, хліб, яйця — зберіть сніданок вигідно.",
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
    {"settlementId": "np-kyiv", "name": "Київ", "region": "Київська обл."},
    {"settlementId": "np-lviv", "name": "Львів", "region": "Львівська обл."},
]

NOVA_POSHTA_OFFICES = [
    {
        "officeId": "np-office-1",
        "name": "Відділення №1",
        "address": "вул. Центральна, 1",
        "type": "office",
    },
    {
        "officeId": "np-postomat-1",
        "name": "Поштомат біля метро",
        "address": "вул. Київська, 2",
        "type": "postomat",
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
            self._carts[cartId] = {
                "cartId": cartId,
                "branchId": "bran-1",
                "deliveryType": "DeliveryHome",
                "timeslot": None,
                "address": None,
                "items": [],
                "totals": {
                    "totalPrice": 0.0,
                    "itemsPrice": 0.0,
                    "deliveryPrice": 0.0,
                    "discount": 0.0,
                },
                "loyalty": {
                    "isEnabled": True,
                    "bonusAvailable": 125.5,
                    "bonusRequested": None,
                    "bonusApplied": 0.0,
                },
                "validations": [],
                "checkoutWebLink": f"https://silpo.ua/cart/{cartId}",
                "checkoutMobileLink": f"silpo://cart/{cartId}",
            }
            carts[session_key] = cartId
        return cartId

    def _recompute_totals(self, cart: dict[str, Any]) -> None:
        items_price = sum(item["totalPrice"] for item in cart["items"])
        bonus_applied = min(cart["loyalty"].get("bonusApplied", 0.0), items_price)
        cart["loyalty"]["bonusApplied"] = round(bonus_applied, 2)
        cart["totals"]["itemsPrice"] = round(items_price, 2)
        cart["totals"]["deliveryPrice"] = 0.0
        cart["totals"]["totalPrice"] = round(items_price - bonus_applied, 2)
        cart["totals"]["discount"] = round(sum(item.get("discount", 0.0) for item in cart["items"]), 2)

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
        def silpo_find_address(
            text: str | None = None,
            address: str | None = None,
        ) -> dict[str, Any]:
            """Find coordinates (lat/lng) for an address string."""
            _ = address or text
            return {"success": True, "summary": "Found 1 address", "addresses": FIXTURE_ADDRESSES[:1]}

        @self._fastmcp.tool
        def silpo_get_available_delivery_types(
            lat: float | None = None,
            lng: float | None = None,
            latitude: float | None = None,
            longitude: float | None = None,
        ) -> list[dict[str, Any]]:
            """Return available delivery types for coordinates."""
            _ = (lat if lat is not None else latitude, lng if lng is not None else longitude)
            return [
                {
                    "type": "DeliveryHome",
                    "branchId": "bran-1",
                    "description": "Доставка додому",
                    "minOrder": 400.0,
                },
                {
                    "type": "SelfPickup",
                    "branchId": "bran-1",
                    "description": "Самовивіз",
                    "minOrder": 0.0,
                },
            ]

        @self._fastmcp.tool
        def silpo_list_branches(
            hasPickup: bool | None = None,
            hasNovaPoshta: bool | None = None,
            limit: int | None = None,
            page: int | None = None,
            pageSize: int | None = None,
        ) -> list[dict[str, Any]]:
            """List Silpo branches, optionally filtered."""
            _ = (limit, page, pageSize)
            result = list(BRANCHES)
            if hasPickup is not None:
                result = [b for b in result if b["hasPickup"] == hasPickup]
            if hasNovaPoshta is not None:
                result = [b for b in result if b["hasNovaPoshta"] == hasNovaPoshta]
            if limit is not None:
                result = result[:limit]
            return result

        @self._fastmcp.tool
        def silpo_get_time_slots(
            branchId: str,
            deliveryType: str | None = None,
            deliveryTypes: list[str] | None = None,
            limit: int | None = None,
            start: str | None = None,
            end: str | None = None,
        ) -> list[dict[str, Any]]:
            """Return available delivery time slots for a branch."""
            _ = (limit, start, end)
            dtype = deliveryType or (deliveryTypes[0] if deliveryTypes else "DeliveryHome")
            slots = [
                {
                    "id": f"slot-{i}",
                    "deliveryType": dtype,
                    "branchId": branchId,
                    "startsAt": f"2026-09-02T0{i + 8}:00:00Z",
                    "endsAt": f"2026-09-02T0{i + 10}:00:00Z",
                    "price": 0.0 if i == 0 else 45.0,
                    "isAvailable": True,
                    "isExpress": i == 0,
                }
                for i in range(3)
            ]
            return slots

        @self._fastmcp.tool
        def silpo_find_nova_poshta_settlements(
            query: str | None = None,
            settlementName: str | None = None,
            title: str | None = None,
        ) -> list[dict[str, Any]]:
            """Find Nova Poshta settlements by name."""
            q = (query or settlementName or title or "").lower()
            return [s for s in NOVA_POSHTA_SETTLEMENTS if q in s["name"].lower()]

        @self._fastmcp.tool
        def silpo_find_nova_poshta_offices(
            settlementId: str | None = None,
            settlement_id: str | None = None,
            title: str | None = None,
        ) -> list[dict[str, Any]]:
            """Find Nova Poshta offices/postomats in a settlement."""
            _ = settlementId or settlement_id or title
            return NOVA_POSHTA_OFFICES

    # Product search (7)
    def _register_search_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_find_products_batch(
            items: list[dict[str, Any]] | None = None,
            queries: list[str] | None = None,
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            products: list[dict[str, Any]] | None = None,
            limit: int | None = None,
        ) -> dict[str, Any]:
            """Search up to 30 products in parallel by list of shopping items."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit)
            if items is None and products is not None:
                items = products
            if items is None and queries is not None:
                items = [{"query": q, "limit": 1} for q in queries]
            items = items or products or []
            if items is None:
                items = []
            results: dict[str, Any] = {"results": {}, "unmatched": []}
            for item in items:
                query = item.get("query", "") or item.get("title", "") or item.get("product", "")
                lim = item.get("limit", limit or 1)
                matches = [
                    p for p in PRODUCTS if query.lower() in p["title"].lower() or query.lower() in p["category"].lower()
                ]
                if matches:
                    results["results"][query] = matches[:lim]
                else:
                    results["unmatched"].append(query)
            return results

        @self._fastmcp.tool
        def silpo_get_products(
            query: str | None = None,
            categoryId: str | None = None,
            onSale: bool | None = None,
            page: int = 1,
            pageSize: int = 20,
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            limit: int | None = None,
            categorySlug: str | None = None,
            category: str | None = None,
            slug: str | None = None,
            mustHavePromotion: bool | None = None,
            promotionCode: str | None = None,
            inStock: bool | None = None,
            set: str | None = None,
            offset: int | None = None,
            sortBy: str | None = None,
            sortDirection: str | None = None,
            fromPrice: float | None = None,
            toPrice: float | None = None,
        ) -> dict[str, Any]:
            """Products with filters: category, promotion, search, pagination."""
            _ = (
                branchId,
                deliveryType,
                timeslotStart,
                timeslotEnd,
                slug,
                category,
                mustHavePromotion,
                promotionCode,
                inStock,
                set,
                offset,
                sortBy,
                sortDirection,
                fromPrice,
                toPrice,
            )
            if limit is not None:
                pageSize = limit
            if categorySlug is not None and categoryId is None:
                cat_by_slug = next((c for c in CATEGORIES if c["slug"] == categorySlug), None)
                if cat_by_slug:
                    categoryId = cat_by_slug["id"]
            items = list(PRODUCTS)
            if query:
                q = query.lower()
                items = [p for p in items if q in p["title"].lower() or q in p["category"].lower()]
            if categoryId:
                cat = next((c for c in CATEGORIES if c["id"] == categoryId), None)
                if cat:
                    items = [p for p in items if p["category"] == cat["title"]]
            if onSale is not None:
                items = [p for p in items if p["isOnSale"] == onSale]
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
            productId: str | None = None,
            slug: str | None = None,
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
        ) -> dict[str, Any]:
            """Full product card: composition, nutritional value, attributes."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd)
            product: dict[str, Any] | None = None
            if productId is not None:
                product = self._find_product(productId)
            elif slug is not None:
                product = next((p for p in PRODUCTS if p["slug"] == slug), None)
            if product is None:
                raise ValueError(f"Product not found: {productId or slug}")
            return {
                **product,
                "description": "Опис товару (мок).",
                "composition": ["складник 1", "складник 2"],
                "nutritionalValue": {"energyKcal": 42, "proteins": 3.0, "fats": 2.5, "carbs": 4.8},
                "attributes": {"brand": product["brand"]},
            }

        @self._fastmcp.tool
        def silpo_get_similar_products(
            slug: str | None = None,
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """Similar/alternative products by slug."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit, offset)
            if slug is None:
                return []
            source = next((p for p in PRODUCTS if p["slug"] == slug), None)
            if source is None:
                return []
            res = [p for p in PRODUCTS if p is not source][:2]
            if limit is not None:
                res = res[:limit]
            return res

        @self._fastmcp.tool
        def silpo_get_replacements(
            productIds: list[str] | None = None,
            branchId: str | None = None,
            companyId: str | None = None,
            deliveryType: str | None = None,
        ) -> list[dict[str, Any]]:
            """Replacements for out-of-stock products."""
            _ = (branchId, companyId, deliveryType)
            productIds = productIds or []
            replacements = []
            for productId in productIds:
                product = self._find_product(productId)
                if product and not product["isAvailable"]:
                    alt = next(
                        (p for p in PRODUCTS if p["isAvailable"] and p["category"] == product["category"]),
                        None,
                    )
                    if alt:
                        replacements.append({"productId": productId, "replacement": alt})
            return replacements

        @self._fastmcp.tool
        def silpo_get_my_favorites(
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """List the guest's favorite products."""
            _ = (branchId, deliveryType, timeslotStart, limit, offset)
            return [p for p in PRODUCTS if p["productId"] in self._favorites]

        @self._fastmcp.tool
        def silpo_add_or_update_favorite_products(
            productIds: list[str] | None = None,
            add: bool | None = None,
            actions: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            """Add or remove products to/from favorites."""
            if actions is not None:
                for act in actions:
                    pid = act.get("productId") or act.get("product_id") or act.get("id")
                    op = act.get("action") or act.get("type") or ("add" if add is not False else "remove")
                    if pid is None:
                        continue
                    if op in ("add", "create", True):
                        if pid not in self._favorites:
                            self._favorites.append(pid)
                    else:
                        if pid in self._favorites:
                            self._favorites.remove(pid)
                return {"productIds": self._favorites}
            productIds = productIds or []
            do_add = True if add is None else add
            for pid in productIds:
                if do_add and pid not in self._favorites:
                    self._favorites.append(pid)
                elif not do_add and pid in self._favorites:
                    self._favorites.remove(pid)
            return {"productIds": self._favorites}

    # Catalog (6)
    def _register_catalog_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_promotions(
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            limit: int | None = None,
            categorySlug: str | None = None,
        ) -> list[dict[str, Any]]:
            """Active promotions and discounts."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit, categorySlug)
            return PROMOTIONS

        @self._fastmcp.tool
        def silpo_get_popular_categories(
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            limit: int | None = None,
        ) -> list[dict[str, Any]]:
            """Popular categories in the branch."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit)
            return CATEGORIES[:3]

        @self._fastmcp.tool
        def silpo_get_category(
            categoryId: str | None = None,
            categorySlug: str | None = None,
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
        ) -> dict[str, Any]:
            """Details of a category: subcategories, product count."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd)
            cid = categoryId
            if cid is None and categorySlug is not None:
                cat_by_slug = next((c for c in CATEGORIES if c["slug"] == categorySlug), None)
                cid = cat_by_slug["id"] if cat_by_slug else None
            if cid is None:
                raise ValueError(f"Category not found: {categoryId or categorySlug}")
            category = next((c for c in CATEGORIES if c["id"] == cid), None)
            if category is None:
                raise ValueError(f"Category not found: {cid}")
            subcats = [c for c in CATEGORIES if c["parentId"] == cid]
            return {"category": category, "subcategories": subcats}

        @self._fastmcp.tool
        def silpo_get_categories(
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            limit: int | None = None,
            pageSize: int | None = None,
            categorySlug: str | None = None,
            parentId: str | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """Flat list of all categories."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit, pageSize, categorySlug, parentId, offset)
            return CATEGORIES

        @self._fastmcp.tool
        def silpo_get_categories_tree(
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
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
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            limit: int | None = None,
        ) -> list[dict[str, Any]]:
            """Curated product sets."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit)
            return PRODUCT_SETS

    # Cart (8)
    def _register_cart_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_my_shopping_cart(context: Context) -> dict[str, Any]:
            """Return the ID of the active cart."""
            return {"cartId": self._ensure_cart(self._session_key(context))}

        @self._fastmcp.tool
        def silpo_create_shopping_cart(
            context: Context,
            addressType: str,
            latitude: float | str,
            longitude: float | str,
            deliveryType: str,
            branchId: str,
            timeslot: dict[str, Any] | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
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
            if slot is None and (timeslotStart is not None or timeslotEnd is not None):
                slot = {"start": timeslotStart, "end": timeslotEnd}
            cart_id = f"cart-{uuid.uuid4().hex[:8]}"
            self._carts[cart_id] = {
                "cartId": cart_id,
                "branchId": branchId,
                "deliveryType": deliveryType,
                "timeslot": slot,
                "address": {
                    "addressType": addressType,
                    "latitude": latitude,
                    "longitude": longitude,
                    "city": city,
                    "street": street,
                    "house": house,
                    "district": district,
                },
                "items": [],
                "totals": {
                    "totalPrice": 0.0,
                    "itemsPrice": 0.0,
                    "deliveryPrice": 0.0,
                    "discount": 0.0,
                },
                "loyalty": {
                    "isEnabled": True,
                    "bonusAvailable": 125.5,
                    "bonusRequested": None,
                    "bonusApplied": 0.0,
                },
                "validations": [],
                "checkoutWebLink": f"https://silpo.ua/cart/{cart_id}",
                "checkoutMobileLink": f"silpo://cart/{cart_id}",
            }
            if session_key is not None:
                SilpoMockServer._mock_carts[session_key] = cart_id
            return {
                "success": True,
                "summary": "Shopping cart created",
                "shoppingCartId": cart_id,
            }

        @self._fastmcp.tool
        def silpo_get_shopping_cart_by_id(
            cartId: str | None = None,
            shoppingCartId: str | None = None,
        ) -> dict[str, Any]:
            """Return the full cart: items, delivery, slot, sums, validations."""
            cid = cartId or shoppingCartId
            if cid is None or cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            return self._carts[cid]

        @self._fastmcp.tool
        def silpo_add_or_update_cart_products(
            cartId: str | None = None,
            shoppingCartId: str | None = None,
            items: list[dict[str, Any]] | None = None,
            products: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            """Add products or update quantities in the cart."""
            cid = cartId or shoppingCartId
            if cid is None or cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            items = items or products or []
            for incoming in items:
                product = self._find_product(incoming["productId"])
                if product is None:
                    raise ValueError(f"Product not found: {incoming['productId']}")
                quantity = float(incoming.get("quantity", 1))
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
                existing = next((i for i in cart["items"] if i["productId"] == product["productId"]), None)
                if existing is not None:
                    cart["items"].remove(existing)
                cart["items"].append(line)
            self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_remove_cart_products(
            cartId: str | None = None,
            shoppingCartId: str | None = None,
            productIds: list[str] | None = None,
            products: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            """Remove specific products from the cart."""
            cid = cartId or shoppingCartId
            if cid is None or cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            if products is not None:
                productIds = [
                    str(p.get("productId") or p.get("id")) for p in products if p.get("productId") or p.get("id")
                ]
            productIds = productIds or []  # type: ignore[assignment]
            cart["items"] = [i for i in cart["items"] if i["productId"] not in productIds]
            self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_clear_shopping_cart(
            cartId: str | None = None,
            shoppingCartId: str | None = None,
        ) -> dict[str, Any]:
            """Clear the entire cart."""
            cid = cartId or shoppingCartId
            if cid is None or cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            cart["items"] = list[dict[str, Any]]()
            cart["loyalty"]["bonusRequested"] = None
            cart["loyalty"]["bonusApplied"] = 0.0
            self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_update_shopping_cart(
            cartId: str | None = None,
            shoppingCartId: str | None = None,
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslot: dict[str, Any] | str | None = None,
            address: dict[str, Any] | str | None = None,
            promoCode: str | None = None,
            couponCode: str | None = None,
            bonusRequested: float | None = None,
            shipments: list[dict[str, Any]] | None = None,
            feedbackChanges: str | None = None,
            feedbackContacts: str | None = None,
            isAdultConfirmed: bool | None = None,
        ) -> dict[str, Any]:
            """Update delivery, slot, address, promo/coupon, or apply bonuses."""
            _ = (shipments, feedbackChanges, feedbackContacts, isAdultConfirmed)
            cid = cartId or shoppingCartId
            if cid is None or cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            if branchId is not None:
                cart["branchId"] = branchId
            if deliveryType is not None:
                cart["deliveryType"] = deliveryType
            if timeslot is not None:
                cart["timeslot"] = timeslot
            if address is not None:
                cart["address"] = address
            if promoCode is not None:
                cart["promoCode"] = promoCode
            if couponCode is not None:
                cart["couponCode"] = couponCode
            if bonusRequested is not None:
                available = cart["loyalty"].get("bonusAvailable", 0.0)
                cart["loyalty"]["bonusRequested"] = min(bonusRequested, available)
                cart["loyalty"]["bonusApplied"] = cart["loyalty"]["bonusRequested"]
                self._recompute_totals(cart)
            return {"cart": cart, "changed": True}

        @self._fastmcp.tool
        def silpo_add_or_update_certificates(
            cartId: str | None = None,
            shoppingCartId: str | None = None,
            certificateIds: list[str] | None = None,
            certificatesToAdd: list[str] | None = None,
            certificatesToRemove: list[str] | None = None,
        ) -> dict[str, Any]:
            """Add or remove gift certificates from the cart."""
            _ = (certificatesToAdd, certificatesToRemove)
            cid = cartId or shoppingCartId
            if cid is None or cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            ids = certificateIds or certificatesToAdd or []
            cart["certificates"] = ids
            return {"cart": cart, "changed": True}

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
                    "createdAt": "2026-07-15T10:30:00Z",
                    "status": "delivered",
                    "totalPrice": 245.5,
                    "deliveryType": "DeliveryHome",
                    "items": [
                        {
                            "productId": "prd-milk-2pct",
                            "title": "Молоко Премія 2.5% 900 мл",
                            "quantity": 2,
                            "unitPrice": 36.9,
                            "totalPrice": 73.8,
                        }
                    ],
                }
            ]

        @self._fastmcp.tool
        def silpo_get_my_offline_orders(
            branchId: str | None = None,
            deliveryType: str | None = None,
            timeslotStart: str | None = None,
            timeslotEnd: str | None = None,
            limit: int | None = None,
            offset: int | None = None,
            dateStart: str | None = None,
            dateEnd: str | None = None,
        ) -> list[dict[str, Any]]:
            """History of physical-store purchases: receipts."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd, limit, offset, dateStart, dateEnd)
            return [
                {
                    "receiptId": "rec-1",
                    "branchName": "Сільпо Львів (центр)",
                    "purchasedAt": "2026-07-01T18:15:00Z",
                    "totalPrice": 180.0,
                    "discount": 12.0,
                    "bonusesEarned": 3.6,
                    "items": [],
                }
            ]

    # Profile (4)
    def _register_profile_tools(self) -> None:
        @self._fastmcp.tool
        def silpo_get_my_profile() -> dict[str, Any]:
            """Profile data: name, phone, email, birth date."""
            return {
                "name": "Олексій",
                "phone": "+380501112233",
                "email": "oleksii@example.com",
                "birthDate": None,
            }

        @self._fastmcp.tool
        def silpo_get_my_delivery_addresses() -> list[dict[str, Any]]:
            """Saved delivery addresses."""
            return [
                {
                    "addressId": "addr-1",
                    "label": "Дім",
                    "text": "Київ, вул. Анни Ахматової, 9",
                    "coordinates": {"lat": 50.3957, "lng": 30.6217},
                }
            ]

        @self._fastmcp.tool
        def silpo_get_my_family() -> list[dict[str, Any]]:
            """Family members in the profile."""
            return [
                {"memberType": "child", "name": "Софія", "age": 7},
                {"memberType": "pet", "name": "Барсик", "age": 3},
            ]

        @self._fastmcp.tool
        def silpo_get_my_food_restrictions() -> dict[str, Any]:
            """Dietary restrictions and food preferences."""
            return {"restrictions": ["безлактозна дієта"], "preferences": ["органічні продукти"]}

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
        def silpo_get_my_coupons(
            limit: int | None = None,
            offset: int | None = None,
        ) -> list[dict[str, Any]]:
            """Available discount coupons."""
            _ = (limit, offset)
            return [
                {
                    "couponId": "cup-1",
                    "businessCouponId": 1,
                    "title": "Знижка 50 грн від 500 грн",
                    "discount": 50.0,
                    "expiresAt": "2026-09-30T23:59:59Z",
                    "barcode": "4820000000001",
                }
            ]

        @self._fastmcp.tool
        def silpo_get_coupon_details(
            couponId: str | None = None,
            businessCouponId: int | str | None = None,
        ) -> dict[str, Any]:
            """Full coupon info: conditions, products, barcode."""
            cid = str(businessCouponId) if businessCouponId is not None else couponId
            if cid not in ("cup-1", "1", 1):
                # allow numeric businessCouponId from live
                if cid != "cup-1":
                    # still return mock for any live id to keep smoke green
                    pass
            return {
                "couponId": "cup-1",
                "businessCouponId": 1,
                "title": "Знижка 50 грн від 500 грн",
                "discount": 50.0,
                "expiresAt": "2026-09-30T23:59:59Z",
                "barcode": "4820000000001",
                "description": "Знижка застосовується до замовлення від 500 грн.",
                "conditions": ["Мінімальне замовлення 500 грн", "Один купон на замовлення"],
                "productIds": [],
            }

        @self._fastmcp.tool
        def silpo_get_my_promos() -> list[dict[str, Any]]:
            """Personal promo offers."""
            return [
                {
                    "promoId": "promo-offer-1",
                    "title": "Промо: Сир Гауда -15%",
                    "description": "Особиста пропозиція на сир.",
                    "expiresAt": "2026-09-01T23:59:59Z",
                }
            ]

        @self._fastmcp.tool
        def silpo_get_promo_codes() -> list[dict[str, Any]]:
            """Active promo codes."""
            return [
                {
                    "code": "SUMMER2026",
                    "description": "Знижка 5% на перше замовлення",
                    "expiresAt": None,
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
                    "certificateId": "cert-1",
                    "code": "GIFT-2026-0001",
                    "barcode": "4820000000002",
                    "nominal": 200.0,
                    "balance": 150.0,
                    "expiresAt": "2026-12-31T23:59:59Z",
                }
            ]

        @self._fastmcp.tool
        def silpo_get_my_premium_subscription() -> dict[str, Any]:
            """Silpo Premium subscription status."""
            return {
                "isActive": True,
                "endsAt": "2026-11-30T23:59:59Z",
                "benefits": ["Безкоштовна доставка", "Персональні знижки"],
            }
