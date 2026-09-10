"""High-level typed client for the Silpo MCP server.

``SilpoClient`` wraps a FastMCP ``Client`` and exposes typed convenience
methods over the documented ``silpo_*`` tools. The same class works against
both the in-memory mock server and the real ``https://mcp.silpo.ua/mcp``
endpoint: only the underlying transport differs.

Because the exact tool schemas are only known from ``tools/list`` at runtime,
``SilpoClient`` is schema-driven: ``list_tools()`` returns the live schemas,
and ``call_tool()`` passes arguments through verbatim. The typed methods are a
stable convenience layer over the documented tool names.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast, overload

from fastmcp import Client as FastMCPClient
from fastmcp.client.client import CallToolResult
from fastmcp.exceptions import ToolError
from mcp.types import TextContent, Tool

if TYPE_CHECKING:
    from silpo_py_mcp.mock_server import SilpoMockServer

from silpo_py_mcp.config import SilpoSettings
from silpo_py_mcp.exceptions import (
    SilpoAuthError,
    SilpoConnectionError,
    SilpoForbiddenError,
    SilpoRateLimitError,
    SilpoToolExecutionError,
    SilpoToolNotFoundError,
    SilpoValidationError,
)
from silpo_py_mcp.models import (
    Address,
    AvailableDeliveryType,
    BatchProductResult,
    Branch,
    CartSummary,
    CartUpdateResult,
    CategoriesTree,
    Category,
    CategoryDetail,
    Certificate,
    Coupon,
    CouponDetail,
    CreateShoppingCartResult,
    DeliveryAddress,
    FamilyMember,
    FoodRestrictions,
    LoyaltyInfo,
    NovaPoshtaOffice,
    NovaPoshtaSettlement,
    OfflineReceipt,
    OnlineOrder,
    PremiumSubscription,
    ProductDetail,
    ProductSearchResult,
    ProductSet,
    Profile,
    Promo,
    PromoCode,
    Promotion,
    SilpoCart,
    SilpoModel,
    SilpoProduct,
    TimeSlot,
)
from silpo_py_mcp.tools import SilpoTool

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=SilpoModel)

_JSONRPC_METHOD_NOT_FOUND = -32601


def _to_plain(value: Any) -> Any:
    """Recursively convert hydrated dataclass ``Root`` objects to plain data.

    The real Silpo server returns tool output as FastMCP's dynamically-created
    ``Root`` dataclasses; normalizing them keeps ``call_tool`` outputs
    JSON-like (dicts/lists) regardless of transport.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _to_plain(dataclasses.asdict(value))
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


def _extract_payload(result: CallToolResult) -> Any:
    """Return the tool output as a Python object, across transports.

    Preference order:
    1. ``result.data`` — hydrated object (FastMCP servers / in-memory).
    2. ``result.structured_content`` — raw structured JSON from the protocol.
    3. ``result.content[0].text`` parsed as JSON.
    """
    if result.data is not None:
        return _to_plain(result.data)
    if result.structured_content is not None:
        return result.structured_content
    for block in result.content:
        if isinstance(block, TextContent):
            text = block.text
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                return text
    raise SilpoValidationError("Tool returned no parseable payload.")


class SilpoClient:
    """Typed client over the Silpo MCP server."""

    def __init__(
        self,
        client: FastMCPClient[Any],
        *,
        settings: SilpoSettings | None = None,
    ) -> None:
        self._client = client
        self._settings = settings or SilpoSettings()

    # -- lifecycle ----------------------------------------------------------

    @classmethod
    def from_fastmcp(cls, client: FastMCPClient[Any], **settings_overrides: Any) -> SilpoClient:
        """Wrap an existing FastMCP client (real transport or in-memory mock)."""
        return cls(client, settings=SilpoSettings(**settings_overrides))

    @classmethod
    def for_real_server(cls, settings: SilpoSettings | None = None) -> SilpoClient:
        """Build a client for the real ``https://mcp.silpo.ua/mcp`` server.

        Uses Streamable HTTP transport with OAuth 2.1/PKCE and encrypted
        on-disk token storage. The first connection opens a browser for login.
        """
        from fastmcp import Client as FastMCPClient
        from fastmcp.client.transports import StreamableHttpTransport

        from silpo_py_mcp.auth import build_encrypted_token_storage, build_oauth

        settings = settings or SilpoSettings()
        storage = build_encrypted_token_storage(
            settings.oauth_storage_dir, encryption_key=settings.oauth_encryption_key
        )
        oauth = build_oauth(
            settings.mcp_url,
            scopes=settings.oauth_scopes,
            client_name=settings.oauth_client_name,
            token_endpoint_auth_method=settings.oauth_token_endpoint_auth_method,
            token_storage=storage,
            callback_port=settings.oauth_callback_port,
            callback_timeout=settings.oauth_callback_timeout,
        )
        transport = StreamableHttpTransport(url=settings.mcp_url)
        client = FastMCPClient(transport, auth=oauth)
        return cls(client, settings=settings)

    @classmethod
    def for_mock(cls, server: SilpoMockServer | None = None) -> SilpoClient:
        """Build a client connected in-memory to a ``SilpoMockServer``.

        Convenience for development and tests — no network or auth needed.
        """
        from silpo_py_mcp.mock_server import SilpoMockServer as MockServer

        server = server or MockServer()
        return cls(FastMCPClient(server.fastmcp))

    async def __aenter__(self) -> SilpoClient:
        await self._client.__aenter__()  # type: ignore[no-untyped-call]
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._client.__aexit__(*exc)  # type: ignore[no-untyped-call]

    # -- low-level, schema-driven -------------------------------------------

    async def list_tools(self) -> list[Tool]:
        """List the live tool schemas from ``tools/list``."""
        return await self._client.list_tools()

    async def call_tool(self, name: SilpoTool | str, arguments: Mapping[str, Any]) -> Any:
        """Call a tool by name and return the parsed payload.

        Arguments are passed through verbatim to the server. Error responses
        are mapped to typed ``Silpo*`` exceptions.
        """
        try:
            result = await self._client.call_tool(str(name), dict(arguments))
        except ToolError as exc:
            self._raise_mapped(name, exc)
            raise
        except Exception as exc:
            raise SilpoConnectionError(f"Failed to call tool '{name}': {exc}") from exc

        if result.is_error:
            self._raise_tool_error(name, result)
        return _extract_payload(result)

    # -- error mapping ------------------------------------------------------

    def _raise_mapped(self, name: SilpoTool | str, exc: ToolError) -> None:
        message = str(exc)
        lowered = message.lower()
        if "not found" in lowered or "method not found" in lowered or "unknown tool" in lowered:
            raise SilpoToolNotFoundError(f"Tool '{name}' not supported by the server: {message}") from exc
        if "429" in message or "rate limit" in lowered or "too many requests" in lowered:
            raise SilpoRateLimitError(f"Rate limited while calling '{name}': {message}") from exc
        if "401" in message or "invalid_token" in lowered or "unauthorized" in lowered:
            raise SilpoAuthError(f"Authentication required/failed for '{name}': {message}") from exc
        if "403" in message or "forbidden" in lowered:
            raise SilpoForbiddenError(f"Access denied for tool '{name}': {message}") from exc
        raise SilpoToolExecutionError(f"Tool '{name}' failed: {message}") from exc

    def _raise_tool_error(self, name: SilpoTool | str, result: CallToolResult) -> None:
        details: list[str] = []
        for block in result.content:
            if isinstance(block, TextContent):
                details.append(str(block.text))
        message = "; ".join(details) or "no details"
        raise SilpoToolExecutionError(f"Tool '{name}' returned an error: {message}")

    # -- payload typing helpers --------------------------------------------

    @overload
    def _validate(self, payload: Any, model: type[T], *, many: Literal[False] = ...) -> T: ...

    @overload
    def _validate(self, payload: Any, model: type[T], *, many: Literal[True]) -> list[T]: ...

    def _validate(self, payload: Any, model: type[T], *, many: bool = False) -> T | list[T]:
        if many:
            if not isinstance(payload, list):
                raise SilpoValidationError(f"Expected a list, got {type(payload).__name__}.")
            return [model.model_validate(item) for item in payload]
        try:
            return model.model_validate(payload)
        except Exception as exc:
            raise SilpoValidationError(f"Response did not match {model.__name__}: {exc}") from exc

    @staticmethod
    def _unwrap_payload(payload: Any, *keys: str) -> Any:
        """Unwrap a live envelope (``{success, summary, <key>, ...}``) into its data.

        Returns the payload unchanged when it is already a list or when none of
        the keys is present, so the mock's documented responses pass through
        untouched. List values are returned directly; dict values (``profile``,
        ``loyalty``, ``coupon``, ``cart``) are returned as-is.
        """
        if not isinstance(payload, dict):
            return payload
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for inner in ("items", "list", "results", "products"):
                    if isinstance(value.get(inner), list):
                        return value[inner]
                return value
        return payload

    # -- Location & delivery (6) --------------------------------------------

    async def find_address(
        self,
        text: str | None = None,
        address: str | None = None,
    ) -> Address:
        """Find coordinates for an address string (first step when changing address)."""
        value = address if address is not None else text
        if value is None:
            raise ValueError("find_address requires text or address")
        payload = await self.call_tool(SilpoTool.FIND_ADDRESS, {"address": value})
        addresses = payload.get("addresses") if isinstance(payload, dict) else None
        if not addresses:
            raise SilpoValidationError("No addresses found in response")
        return self._validate(addresses[0], Address)

    async def get_available_delivery_types(
        self,
        lat: float | None = None,
        lng: float | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> list[AvailableDeliveryType]:
        """Return delivery types available for a coordinate."""
        lat_val = lat if lat is not None else latitude
        lng_val = lng if lng is not None else longitude
        if lat_val is None or lng_val is None:
            raise ValueError("get_available_delivery_types requires lat/lng or latitude/longitude")
        payload = await self.call_tool(
            SilpoTool.GET_AVAILABLE_DELIVERY_TYPES,
            {"latitude": lat_val, "longitude": lng_val},
        )
        payload = self._unwrap_payload(payload, "options")
        return self._validate(payload, AvailableDeliveryType, many=True)

    async def list_branches(
        self,
        has_pickup: bool | None = None,
        has_nova_poshta: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Branch]:
        """List Silpo branches, optionally filtered.

        The real server returns an envelope (``{"branches": [...], ...}``);
        the mock returns a bare list.
        """
        args: dict[str, Any] = {}
        if has_pickup is not None:
            args["hasPickup"] = has_pickup
        if has_nova_poshta is not None:
            args["hasNP"] = has_nova_poshta
        if limit is not None:
            args["limit"] = limit
        if offset is not None:
            args["offset"] = offset
        payload = await self.call_tool(SilpoTool.LIST_BRANCHES, args)
        if isinstance(payload, dict):
            for key in ("branches", "items", "data", "results"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break
        return self._validate(payload, Branch, many=True)

    async def get_time_slots(
        self,
        branch_id: str,
        delivery_type: str | None = None,
        delivery_types: list[str] | None = None,
        limit: int | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[TimeSlot]:
        """Return delivery time slots for a branch (call after getting the cart)."""
        dtype = delivery_type or (delivery_types[0] if delivery_types else None)
        if dtype is None:
            raise ValueError("get_time_slots requires delivery_type or delivery_types")
        args: dict[str, Any] = {"branchId": branch_id, "deliveryTypes": [dtype]}
        if limit is not None:
            args["limit"] = limit
        if start is not None:
            args["start"] = start
        if end is not None:
            args["end"] = end
        payload = await self.call_tool(SilpoTool.GET_TIME_SLOTS, args)
        payload = self._unwrap_payload(payload, "slots")
        return self._validate(payload, TimeSlot, many=True)

    async def find_nova_poshta_settlements(
        self,
        query: str | None = None,
        settlement_name: str | None = None,
    ) -> list[NovaPoshtaSettlement]:
        """Find Nova Poshta settlements by name."""
        value = query if query is not None else settlement_name
        if value is None:
            raise ValueError("find_nova_poshta_settlements requires query or settlement_name")
        payload = await self.call_tool(SilpoTool.FIND_NOVA_POSHTA_SETTLEMENTS, {"title": value})
        payload = self._unwrap_payload(payload, "settlements")
        return self._validate(payload, NovaPoshtaSettlement, many=True)

    async def find_nova_poshta_offices(self, settlement_id: str) -> list[NovaPoshtaOffice]:
        """Find Nova Poshta offices/postomats in a settlement."""
        payload = await self.call_tool(SilpoTool.FIND_NOVA_POSHTA_OFFICES, {"settlementId": settlement_id})
        payload = self._unwrap_payload(payload, "offices")
        return self._validate(payload, NovaPoshtaOffice, many=True)

    # -- Product search (7) -------------------------------------------------

    async def find_products_batch(
        self,
        branch_id: str,
        delivery_type: str,
        timeslot_start: str,
        timeslot_end: str,
        queries: list[str],
        limit: int | None = None,
    ) -> BatchProductResult:
        """Search up to 30 products in parallel from a shopping list."""
        args: dict[str, Any] = {
            "branchId": branch_id,
            "deliveryType": delivery_type,
            "timeslotStart": timeslot_start,
            "timeslotEnd": timeslot_end,
            "products": queries,
        }
        if limit is not None:
            args["limit"] = limit
        payload = await self.call_tool(SilpoTool.FIND_PRODUCTS_BATCH, args)
        if isinstance(payload, dict) and isinstance(payload.get("queries"), list):
            results: dict[str, Any] = {}
            unmatched: list[str] = []
            for entry in payload["queries"]:
                query = entry.get("query")
                matches = entry.get("products") or []
                if query and matches:
                    results[query] = matches
                elif query:
                    unmatched.append(query)
            payload = {"results": results, "unmatched": unmatched}
        return self._validate(payload, BatchProductResult)

    async def get_products(
        self,
        branch_id: str,
        delivery_type: str,
        timeslot_start: str,
        timeslot_end: str,
        *,
        category: str | None = None,
        promotion_code: str | None = None,
        in_stock: bool | None = None,
        must_have_promotion: bool | None = None,
        product_set: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
        from_price: float | None = None,
        to_price: float | None = None,
    ) -> ProductSearchResult:
        """Products with filters: category, promotion, stock, price, pagination.

        At least one of ``category``/``must_have_promotion``/``promotion_code``/
        ``product_set`` is required by the server. Sort order caveat: the API
        sorts in-stock and out-of-stock products independently within each
        group, so set ``in_stock=True`` for a single continuously-sorted list.
        """
        args: dict[str, Any] = {
            "branchId": branch_id,
            "deliveryType": delivery_type,
            "timeslotStart": timeslot_start,
            "timeslotEnd": timeslot_end,
        }
        if category is not None:
            args["category"] = category
        if promotion_code is not None:
            args["promotionCode"] = promotion_code
        if in_stock is not None:
            args["inStock"] = in_stock
        if must_have_promotion is not None:
            args["mustHavePromotion"] = must_have_promotion
        if product_set is not None:
            args["set"] = product_set
        if limit is not None:
            args["limit"] = limit
        if offset is not None:
            args["offset"] = offset
        if sort_by is not None:
            args["sortBy"] = sort_by
        if sort_direction is not None:
            args["sortDirection"] = sort_direction
        if from_price is not None:
            args["fromPrice"] = from_price
        if to_price is not None:
            args["toPrice"] = to_price
        payload = await self.call_tool(SilpoTool.GET_PRODUCTS, args)
        if isinstance(payload, dict) and isinstance(payload.get("products"), list):
            items = payload["products"]
            meta = payload.get("meta")
            total = meta.get("total") if isinstance(meta, dict) else None
            payload = {
                "items": items,
                "total": total if total is not None else len(items),
                "page": 1,
                "pageSize": len(items),
                "hasMore": False,
            }
        return self._validate(payload, ProductSearchResult)

    async def get_product_details(
        self,
        branch_id: str,
        slug: str,
        delivery_type: str,
        timeslot_start: str,
        timeslot_end: str,
    ) -> ProductDetail:
        """Full product card: price, stock, images, attributes, package size."""
        payload = await self.call_tool(
            SilpoTool.GET_PRODUCT_DETAILS,
            {
                "branchId": branch_id,
                "slug": slug,
                "deliveryType": delivery_type,
                "timeslotStart": timeslot_start,
                "timeslotEnd": timeslot_end,
            },
        )
        payload = self._unwrap_payload(payload, "product")
        return self._validate(payload, ProductDetail)

    async def get_similar_products(
        self,
        branch_id: str,
        slug: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        delivery_type: str | None = None,
    ) -> list[SilpoProduct]:
        """Similar/alternative products by slug."""
        args: dict[str, Any] = {"branchId": branch_id, "slug": slug}
        if limit is not None:
            args["limit"] = limit
        if offset is not None:
            args["offset"] = offset
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        payload = await self.call_tool(SilpoTool.GET_SIMILAR_PRODUCTS, args)
        payload = self._unwrap_payload(payload, "products")
        return self._validate(payload, SilpoProduct, many=True)

    async def get_replacements(
        self,
        branch_id: str,
        company_id: str,
        delivery_type: str,
        product_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Replacements for out-of-stock products."""
        payload = await self.call_tool(
            SilpoTool.GET_REPLACEMENTS,
            {"branchId": branch_id, "companyId": company_id, "deliveryType": delivery_type, "productIds": product_ids},
        )
        payload = self._unwrap_payload(payload, "items")
        return cast(list[dict[str, Any]], payload)

    async def get_favorites(self, branch_id: str, delivery_type: str, timeslot_start: str) -> list[SilpoProduct]:
        """List the guest's favorite products."""
        payload = await self.call_tool(
            SilpoTool.GET_MY_FAVORITES,
            {"branchId": branch_id, "deliveryType": delivery_type, "timeslotStart": timeslot_start},
        )
        return self._validate(payload, SilpoProduct, many=True)

    async def update_favorites(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Add or remove products to/from favorites.

        ``actions`` entries need ``productId`` + ``externalProductId`` (both
        from any product-returning tool) plus ``toDelete`` (true to remove).
        """
        payload = await self.call_tool(SilpoTool.ADD_OR_UPDATE_FAVORITE_PRODUCTS, {"actions": actions})
        return cast(dict[str, Any], payload)

    # -- Catalog (6) --------------------------------------------------------

    async def get_promotions(
        self,
        branch_id: str,
        delivery_type: str,
        timeslot_start: str,
        timeslot_end: str,
    ) -> list[Promotion]:
        """Active promotions and discounts for a branch."""
        payload = await self.call_tool(
            SilpoTool.GET_PROMOTIONS,
            {
                "branchId": branch_id,
                "deliveryType": delivery_type,
                "timeslotStart": timeslot_start,
                "timeslotEnd": timeslot_end,
            },
        )
        payload = self._unwrap_payload(payload, "promotions")
        return self._validate(payload, Promotion, many=True)

    async def get_popular_categories(self, branch_id: str, delivery_type: str) -> list[Category]:
        """Popular categories in the branch."""
        payload = await self.call_tool(
            SilpoTool.GET_POPULAR_CATEGORIES, {"branchId": branch_id, "deliveryType": delivery_type}
        )
        payload = self._unwrap_payload(payload, "categories")
        return self._validate(payload, Category, many=True)

    async def get_category(
        self,
        branch_id: str,
        delivery_type: str,
        category_slug: str,
    ) -> CategoryDetail:
        """Details of a category: subcategories, product count."""
        payload = await self.call_tool(
            SilpoTool.GET_CATEGORY,
            {"branchId": branch_id, "deliveryType": delivery_type, "categorySlug": category_slug},
        )
        if isinstance(payload, dict):
            category = payload.get("category")
            if isinstance(category, dict) and isinstance(category.get("children"), list):
                payload = {**payload, "subcategories": category["children"]}
        return self._validate(payload, CategoryDetail)

    async def get_categories(
        self,
        branch_id: str,
        *,
        parent_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Category]:
        """Flat list of all categories."""
        args: dict[str, Any] = {"branchId": branch_id}
        if parent_id is not None:
            args["parentId"] = parent_id
        if limit is not None:
            args["limit"] = limit
        if offset is not None:
            args["offset"] = offset
        payload = await self.call_tool(SilpoTool.GET_CATEGORIES, args)
        payload = self._unwrap_payload(payload, "categories")
        return self._validate(payload, Category, many=True)

    async def get_categories_tree(
        self,
        branch_id: str,
        delivery_type: str,
        timeslot_start: str,
        timeslot_end: str,
    ) -> CategoriesTree:
        """Full category tree."""
        payload = await self.call_tool(
            SilpoTool.GET_CATEGORIES_TREE,
            {
                "branchId": branch_id,
                "deliveryType": delivery_type,
                "timeslotStart": timeslot_start,
                "timeslotEnd": timeslot_end,
            },
        )
        if isinstance(payload, dict) and isinstance(payload.get("tree"), list):
            payload = {"rootCategories": payload["tree"]}
        return self._validate(payload, CategoriesTree)

    async def get_product_sets(
        self,
        branch_id: str,
        *,
        delivery_type: str | None = None,
    ) -> list[ProductSet]:
        """Curated product sets."""
        args: dict[str, Any] = {"branchId": branch_id}
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        payload = await self.call_tool(SilpoTool.GET_PRODUCT_SETS, args)
        payload = self._unwrap_payload(payload, "sets")
        return self._validate(payload, ProductSet, many=True)

    # -- Cart (8) -----------------------------------------------------------

    async def get_cart(self) -> CartSummary:
        """Return the ID of the active cart (always the first step)."""
        payload = await self.call_tool(SilpoTool.GET_MY_SHOPPING_CART, {})
        return self._validate(payload, CartSummary)

    async def create_shopping_cart(
        self,
        *,
        address_type: str,
        latitude: float | str,
        longitude: float | str,
        delivery_type: str,
        branch_id: str,
        timeslot_start: str,
        timeslot_end: str,
        city: str | None = None,
        street: str | None = None,
        house: str | None = None,
        district: str | None = None,
    ) -> CreateShoppingCartResult:
        """Create a cart when ``get_cart`` reports ``exists: false``.

        Idempotent: if a cart already exists the server returns the existing
        ``shoppingCartId``. Resolve ``latitude``/``longitude`` via
        ``find_address``, ``delivery_type``/``branch_id`` via
        ``get_available_delivery_types`` and the slot via ``get_time_slots``.
        """
        args: dict[str, Any] = {
            "addressType": address_type,
            "latitude": latitude,
            "longitude": longitude,
            "deliveryType": delivery_type,
            "branchId": branch_id,
            "timeslot": {"start": timeslot_start, "end": timeslot_end},
        }
        if city is not None:
            args["city"] = city
        if street is not None:
            args["street"] = street
        if house is not None:
            args["house"] = house
        if district is not None:
            args["district"] = district
        payload = await self.call_tool(SilpoTool.CREATE_SHOPPING_CART, args)
        return self._validate(payload, CreateShoppingCartResult)

    async def get_cart_by_id(self, cart_id: str) -> SilpoCart:
        """Return the full cart: items, delivery, slot, sums, validations."""
        payload = await self.call_tool(SilpoTool.GET_SHOPPING_CART_BY_ID, {"shoppingCartId": cart_id})
        if isinstance(payload, dict) and isinstance(payload.get("cart"), dict):
            cart = dict(payload["cart"])
            cart.setdefault("loyalty", payload.get("loyalty"))
            cart.setdefault("checkoutWebLink", payload.get("checkoutWebLink"))
            cart.setdefault("checkoutMobileLink", payload.get("checkoutMobileLink"))
            shipments = cart.get("shipments")
            if not cart.get("branchId") and isinstance(shipments, list) and shipments:
                first = shipments[0]
                if isinstance(first, dict) and first.get("branchId"):
                    cart["branchId"] = first["branchId"]
            calculation = cart.get("calculation")
            if isinstance(calculation, dict):
                if isinstance(calculation.get("validations"), list):
                    cart["validations"] = calculation["validations"]
                totals = cart.get("totals")
                if not isinstance(totals, dict) or not totals.get("totalPrice"):
                    delivery = calculation.get("delivery") or {}
                    cart["totals"] = {
                        "totalPrice": calculation.get("total", 0.0),
                        "itemsPrice": calculation.get("subTotal", 0.0),
                        "deliveryPrice": delivery.get("total", 0.0) if isinstance(delivery, dict) else 0.0,
                        "discount": calculation.get("subDiscount", 0.0),
                    }
            payload = cart
        else:
            payload = self._unwrap_payload(payload, "cart")
        return self._validate(payload, SilpoCart)

    async def add_or_update_cart_products(
        self,
        cart_id: str,
        products: list[dict[str, Any]],
    ) -> CartUpdateResult:
        """Add products or update quantities in the cart.

        ``products`` entries need ``productId`` + ``companyId`` + ``branchId``
        (as returned by product search) plus a ``quantity``.
        """
        payload = await self.call_tool(
            SilpoTool.ADD_OR_UPDATE_CART_PRODUCTS, {"shoppingCartId": cart_id, "products": products}
        )
        return self._validate(payload, CartUpdateResult)

    async def remove_cart_products(self, cart_id: str, product_ids: list[str]) -> CartUpdateResult:
        """Remove specific products from the cart."""
        products = [{"productId": pid} for pid in product_ids]
        payload = await self.call_tool(
            SilpoTool.REMOVE_CART_PRODUCTS, {"shoppingCartId": cart_id, "products": products}
        )
        return self._validate(payload, CartUpdateResult)

    async def clear_cart(self, cart_id: str) -> CartUpdateResult:
        """Clear the entire cart."""
        payload = await self.call_tool(SilpoTool.CLEAR_SHOPPING_CART, {"shoppingCartId": cart_id})
        return self._validate(payload, CartUpdateResult)

    async def update_shopping_cart(
        self,
        cart_id: str,
        delivery_type: str,
        timeslot: dict[str, Any],
        address: dict[str, Any],
        shipments: list[dict[str, Any]],
        *,
        branch_id: str | None = None,
        promo_code: str | None = None,
        bonus_requested: float | None = None,
        feedback_changes: str | None = None,
        feedback_contacts: str | None = None,
        is_adult_confirmed: bool | None = None,
    ) -> CartUpdateResult:
        """Update delivery, slot, address, shipments, or apply bonuses."""
        args: dict[str, Any] = {
            "shoppingCartId": cart_id,
            "deliveryType": delivery_type,
            "timeslot": timeslot,
            "address": address,
            "shipments": shipments,
        }
        if branch_id is not None:
            args["branchId"] = branch_id
        if promo_code is not None:
            args["promoCode"] = promo_code
        if bonus_requested is not None:
            args["bonusRequested"] = bonus_requested
        if feedback_changes is not None:
            args["feedbackChanges"] = feedback_changes
        if feedback_contacts is not None:
            args["feedbackContacts"] = feedback_contacts
        if is_adult_confirmed is not None:
            args["isAdultConfirmed"] = is_adult_confirmed
        payload = await self.call_tool(SilpoTool.UPDATE_SHOPPING_CART, args)
        return self._validate(payload, CartUpdateResult)

    async def add_or_update_certificates(
        self, cart_id: str, certificate_ids: list[str | dict[str, Any]]
    ) -> CartUpdateResult:
        """Add or remove gift certificates from the cart.

        Entries are certificate barcodes (plain strings) or
        ``{"barcode": ..., "pincode": ...}`` dicts; strings are sent through
        as ``{"barcode": ...}`` per the live schema.
        """
        to_add = [{"barcode": c} if isinstance(c, str) else c for c in certificate_ids]
        payload = await self.call_tool(
            SilpoTool.ADD_OR_UPDATE_CERTIFICATES,
            {"shoppingCartId": cart_id, "certificatesToAdd": to_add, "certificatesToRemove": []},
        )
        return self._validate(payload, CartUpdateResult)

    # -- Orders (2) ---------------------------------------------------------

    async def get_online_orders(self, limit: int | None = None, offset: int | None = None) -> list[OnlineOrder]:
        """History of online orders."""
        args: dict[str, Any] = {}
        if limit is not None:
            args["limit"] = limit
        if offset is not None:
            args["offset"] = offset
        payload = await self.call_tool(SilpoTool.GET_MY_ONLINE_ORDERS, args)
        payload = self._unwrap_payload(payload, "orders")
        return self._validate(payload, OnlineOrder, many=True)

    async def get_offline_orders(
        self,
        branch_id: str,
        delivery_type: str,
        timeslot_start: str,
        timeslot_end: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[OfflineReceipt]:
        """History of physical-store purchases (receipts)."""
        args: dict[str, Any] = {
            "branchId": branch_id,
            "deliveryType": delivery_type,
            "timeslotStart": timeslot_start,
            "timeslotEnd": timeslot_end,
        }
        if limit is not None:
            args["limit"] = limit
        if offset is not None:
            args["offset"] = offset
        if date_start is not None:
            args["dateStart"] = date_start
        if date_end is not None:
            args["dateEnd"] = date_end
        payload = await self.call_tool(SilpoTool.GET_MY_OFFLINE_ORDERS, args)
        payload = self._unwrap_payload(payload, "orders")
        return self._validate(payload, OfflineReceipt, many=True)

    # -- Profile (4) --------------------------------------------------------

    async def get_profile(self) -> Profile:
        """Profile data: name, phone, email, birth date."""
        payload = await self.call_tool(SilpoTool.GET_MY_PROFILE, {})
        payload = self._unwrap_payload(payload, "profile")
        return self._validate(payload, Profile)

    async def get_delivery_addresses(self) -> list[DeliveryAddress]:
        """Saved delivery addresses."""
        payload = await self.call_tool(SilpoTool.GET_MY_DELIVERY_ADDRESSES, {})
        payload = self._unwrap_payload(payload, "addresses")
        return self._validate(payload, DeliveryAddress, many=True)

    async def get_family(self) -> list[FamilyMember]:
        """Family members in the profile."""
        payload = await self.call_tool(SilpoTool.GET_MY_FAMILY, {})
        payload = self._unwrap_payload(payload, "members")
        return self._validate(payload, FamilyMember, many=True)

    async def get_food_restrictions(self) -> FoodRestrictions:
        """Dietary restrictions and food preferences."""
        payload = await self.call_tool(SilpoTool.GET_MY_FOOD_RESTRICTIONS, {})
        return self._validate(payload, FoodRestrictions)

    # -- Loyalty & promotions (7) -------------------------------------------

    async def get_loyalty_info(self) -> LoyaltyInfo:
        """Vlasnyi Rakunok loyalty card info."""
        payload = await self.call_tool(SilpoTool.GET_LOYALTY_INFO, {})
        payload = self._unwrap_payload(payload, "loyalty")
        return self._validate(payload, LoyaltyInfo)

    async def get_coupons(self) -> list[Coupon]:
        """Available discount coupons."""
        payload = await self.call_tool(SilpoTool.GET_MY_COUPONS, {})
        payload = self._unwrap_payload(payload, "coupons")
        return self._validate(payload, Coupon, many=True)

    async def get_coupon_details(self, business_coupon_id: int | float | str) -> CouponDetail:
        """Full coupon info: eligibility, conditions, reward, progress.

        Check ``can_be_applied_to_order`` for eligibility — it requires both
        the user toggle (``active``) and the lifecycle ``state`` to allow use.
        """
        payload = await self.call_tool(SilpoTool.GET_COUPON_DETAILS, {"businessCouponId": business_coupon_id})
        payload = self._unwrap_payload(payload, "coupon")
        return self._validate(payload, CouponDetail)

    async def get_promos(self) -> list[Promo]:
        """Personal promo offers."""
        payload = await self.call_tool(SilpoTool.GET_MY_PROMOS, {})
        payload = self._unwrap_payload(payload, "promos")
        return self._validate(payload, Promo, many=True)

    async def get_promo_codes(self) -> list[PromoCode]:
        """Active promo codes."""
        payload = await self.call_tool(SilpoTool.GET_PROMO_CODES, {})
        payload = self._unwrap_payload(payload, "promoCodes")
        return self._validate(payload, PromoCode, many=True)

    async def get_certificates(self, limit: int | None = None, offset: int | None = None) -> list[Certificate]:
        """Active gift certificates."""
        args: dict[str, Any] = {}
        if limit is not None:
            args["limit"] = limit
        if offset is not None:
            args["offset"] = offset
        payload = await self.call_tool(SilpoTool.GET_MY_CERTIFICATES, args)
        payload = self._unwrap_payload(payload, "certificates")
        return self._validate(payload, Certificate, many=True)

    async def get_premium_subscription(self) -> PremiumSubscription:
        """Silpo Premium subscription status."""
        payload = await self.call_tool(SilpoTool.GET_MY_PREMIUM_SUBSCRIPTION, {})
        return self._validate(payload, PremiumSubscription)
