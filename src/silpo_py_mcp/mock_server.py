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
        def silpo_find_address(address: str) -> dict[str, Any]:
            """Find coordinates (lat/lng) for an address string."""
            return {"success": True, "summary": "Found 1 address", "addresses": FIXTURE_ADDRESSES[:1]}

        @self._fastmcp.tool
        def silpo_get_available_delivery_types(
            latitude: float,
            longitude: float,
        ) -> list[dict[str, Any]]:
            """Return available delivery types for coordinates."""
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
            limit: int | None = None,
            start: str | None = None,
            end: str | None = None,
        ) -> list[dict[str, Any]]:
            """Return available delivery time slots for a branch."""
            _ = (limit, start, end)
            dtype = deliveryTypes[0] if deliveryTypes else "DeliveryHome"
            slots = [
                {
                    "id": f"slot-{i}",
                    "deliveryType": dtype,
                    "branchId": branchId,
                    "startsAt": f"2026-09-02T0{i + 8}:00:00Z",
                    "endsAt": f"2026-09-02T0{i + 10}:00:00Z",
                    "start": f"2026-09-02T0{i + 8}:00:00Z",
                    "end": f"2026-09-02T0{i + 10}:00:00Z",
                    "price": 0.0 if i == 0 else 45.0,
                    "deliveryCost": 0.0 if i == 0 else 45.0,
                    "minOrderCost": 199.0,
                    "isAvailable": True,
                    "available": True,
                    "isExpress": i == 0,
                }
                for i in range(3)
            ]
            return slots

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
            """Products with filters: category, promotion, stock, pagination."""
            _ = (deliveryType, timeslotStart, timeslotEnd, promotionCode, set, sortBy, sortDirection)
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
            """Full product card: price, stock, images, attributes."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd)
            product = next((p for p in PRODUCTS if p["slug"] == slug), None)
            if product is None:
                raise ValueError(f"Product not found: {slug}")
            return {
                "id": product["productId"],
                "name": product["title"],
                "slug": product["slug"],
                "price": product["price"],
                "displayPrice": product.get("displayPrice", product["price"]),
                "oldPrice": product["oldPrice"],
                "stock": product.get("stock", 10.0),
                "available": product["isAvailable"],
                "image": product.get("imageUrl"),
                "weighted": product.get("weighted", False),
                "step": product.get("step", 1.0),
                "ratio": product.get("unit", "шт"),
                "displayRatio": product.get("displayRatio"),
                "specialPrices": product.get("specialPrices"),
                "companyId": product["companyId"],
                "branchId": product["branchId"],
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
            """Active promotions and discounts."""
            _ = (branchId, deliveryType, timeslotStart, timeslotEnd)
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
            """Details of a category: subcategories, product count."""
            _ = (branchId, deliveryType)
            cat_by_slug = next((c for c in CATEGORIES if c["slug"] == categorySlug), None)
            cid = cat_by_slug["id"] if cat_by_slug else None
            if cid is None:
                raise ValueError(f"Category not found: {categorySlug}")
            category = next((c for c in CATEGORIES if c["id"] == cid), None)
            if category is None:
                raise ValueError(f"Category not found: {cid}")
            subcats = [c for c in CATEGORIES if c["parentId"] == cid]
            return {
                "success": True,
                "category": {
                    **category,
                    "path": None,
                    "priceRange": None,
                    "children": [{"id": c["id"], "slug": c["slug"], "title": c["title"]} for c in subcats],
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
        def silpo_get_shopping_cart_by_id(shoppingCartId: str) -> dict[str, Any]:
            """Return the full cart: items, delivery, slot, sums, validations."""
            if shoppingCartId not in self._carts:
                raise ValueError(f"Cart not found: {shoppingCartId}")
            return self._carts[shoppingCartId]

        @self._fastmcp.tool
        def silpo_add_or_update_cart_products(
            shoppingCartId: str,
            products: list[dict[str, Any]],
        ) -> dict[str, Any]:
            """Add products or update quantities in the cart."""
            cid = shoppingCartId
            if cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            for incoming in products:
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
            """Update delivery, slot, address, shipments, or apply bonuses."""
            cid = shoppingCartId
            if cid not in self._carts:
                raise ValueError(f"Cart not found: {cid}")
            cart = self._carts[cid]
            cart["deliveryType"] = deliveryType
            cart["timeslot"] = timeslot
            cart["address"] = address
            cart["shipments"] = shipments
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
        def silpo_get_coupon_details(businessCouponId: int | float) -> dict[str, Any]:
            """Full coupon info: eligibility, conditions, reward, progress."""
            _ = businessCouponId  # mock returns the fixture coupon for any id
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
