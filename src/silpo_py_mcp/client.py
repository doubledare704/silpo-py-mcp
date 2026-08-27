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
from mcp.types import Tool

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
        if hasattr(block, "text"):
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

    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any:
        """Call a tool by name and return the parsed payload.

        Arguments are passed through verbatim to the server. Error responses
        are mapped to typed ``Silpo*`` exceptions.
        """
        try:
            result = await self._client.call_tool(name, dict(arguments))
        except ToolError as exc:
            self._raise_mapped(name, exc)
            raise
        except Exception as exc:
            raise SilpoConnectionError(f"Failed to call tool '{name}': {exc}") from exc

        if result.is_error:
            self._raise_tool_error(name, result)
        return _extract_payload(result)

    # -- error mapping ------------------------------------------------------

    def _raise_mapped(self, name: str, exc: ToolError) -> None:
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

    def _raise_tool_error(self, name: str, result: CallToolResult) -> None:
        details: list[str] = []
        for block in result.content:
            if hasattr(block, "text"):
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
        payload = await self.call_tool("silpo_find_address", {"text": value, "address": value})
        return self._validate(payload, Address)

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
            "silpo_get_available_delivery_types",
            {"lat": lat_val, "lng": lng_val, "latitude": lat_val, "longitude": lng_val},
        )
        return self._validate(payload, AvailableDeliveryType, many=True)

    async def list_branches(
        self,
        has_pickup: bool | None = None,
        has_nova_poshta: bool | None = None,
        limit: int | None = None,
    ) -> list[Branch]:
        """List Silpo branches, optionally filtered."""
        args: dict[str, Any] = {}
        if has_pickup is not None:
            args["hasPickup"] = has_pickup
        if has_nova_poshta is not None:
            args["hasNovaPoshta"] = has_nova_poshta
        if limit is not None:
            args["limit"] = limit
        payload = await self.call_tool("silpo_list_branches", args)
        return self._validate(payload, Branch, many=True)

    async def get_time_slots(
        self,
        branch_id: str,
        delivery_type: str | None = None,
        delivery_types: list[str] | None = None,
    ) -> list[TimeSlot]:
        """Return delivery time slots for a branch (call after getting the cart)."""
        dtype = delivery_type or (delivery_types[0] if delivery_types else None)
        if dtype is None:
            raise ValueError("get_time_slots requires delivery_type or delivery_types")
        payload = await self.call_tool(
            "silpo_get_time_slots",
            {"branchId": branch_id, "deliveryType": dtype, "deliveryTypes": [dtype]},
        )
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
        payload = await self.call_tool("silpo_find_nova_poshta_settlements", {"query": value, "settlementName": value})
        return self._validate(payload, NovaPoshtaSettlement, many=True)

    async def find_nova_poshta_offices(self, settlement_id: str) -> list[NovaPoshtaOffice]:
        """Find Nova Poshta offices/postomats in a settlement."""
        payload = await self.call_tool(
            "silpo_find_nova_poshta_offices", {"settlementId": settlement_id, "settlement_id": settlement_id}
        )
        return self._validate(payload, NovaPoshtaOffice, many=True)

    # -- Product search (7) -------------------------------------------------

    async def find_products_batch(self, queries: list[str], limit: int = 1) -> BatchProductResult:
        """Search up to 30 products in parallel from a shopping list."""
        items = [{"query": q, "limit": limit} for q in queries]
        payload = await self.call_tool("silpo_find_products_batch", {"items": items, "queries": queries})
        return self._validate(payload, BatchProductResult)

    async def get_products(
        self,
        query: str | None = None,
        category_id: str | None = None,
        on_sale: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
        limit: int | None = None,
        category_slug: str | None = None,
    ) -> ProductSearchResult:
        """Products with filters: category, promotion, search, pagination."""
        args: dict[str, Any] = {"page": page, "pageSize": page_size}
        if query is not None:
            args["query"] = query
        if category_id is not None:
            args["categoryId"] = category_id
        if category_slug is not None:
            args["categorySlug"] = category_slug
        if on_sale is not None:
            args["onSale"] = on_sale
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        if limit is not None:
            args["limit"] = limit
            args["pageSize"] = limit
        payload = await self.call_tool("silpo_get_products", args)
        return self._validate(payload, ProductSearchResult)

    async def get_product_details(
        self,
        product_id: str | None = None,
        slug: str | None = None,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> ProductDetail:
        """Full product card: composition, nutritional value, attributes."""
        if product_id is None and slug is None:
            raise ValueError("get_product_details requires product_id or slug")
        args: dict[str, Any] = {}
        if product_id is not None:
            args["productId"] = product_id
        if slug is not None:
            args["slug"] = slug
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_product_details", args)
        return self._validate(payload, ProductDetail)

    async def get_similar_products(
        self,
        slug: str,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> list[SilpoProduct]:
        """Similar/alternative products by slug."""
        args: dict[str, Any] = {"slug": slug}
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_similar_products", args)
        return self._validate(payload, SilpoProduct, many=True)

    async def get_replacements(self, product_ids: list[str]) -> list[dict[str, Any]]:
        """Replacements for out-of-stock products."""
        payload = await self.call_tool("silpo_get_replacements", {"productIds": product_ids})
        return cast(list[dict[str, Any]], payload)

    async def get_favorites(self) -> list[SilpoProduct]:
        """List the guest's favorite products."""
        payload = await self.call_tool("silpo_get_my_favorites", {})
        return self._validate(payload, SilpoProduct, many=True)

    async def update_favorites(self, product_ids: list[str], add: bool = True) -> dict[str, Any]:
        """Add or remove products to/from favorites."""
        payload = await self.call_tool("silpo_add_or_update_favorite_products", {"productIds": product_ids, "add": add})
        return cast(dict[str, Any], payload)

    # -- Catalog (6) --------------------------------------------------------

    async def get_promotions(
        self,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> list[Promotion]:
        """Active promotions and discounts for a branch."""
        args: dict[str, Any] = {}
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_promotions", args)
        return self._validate(payload, Promotion, many=True)

    async def get_popular_categories(
        self,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> list[Category]:
        """Popular categories in the branch."""
        args: dict[str, Any] = {}
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_popular_categories", args)
        return self._validate(payload, Category, many=True)

    async def get_category(
        self,
        category_id: str | None = None,
        category_slug: str | None = None,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> CategoryDetail:
        """Details of a category: subcategories, product count."""
        if category_id is None and category_slug is None:
            raise ValueError("get_category requires category_id or category_slug")
        args: dict[str, Any] = {}
        if category_id is not None:
            args["categoryId"] = category_id
        if category_slug is not None:
            args["categorySlug"] = category_slug
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_category", args)
        return self._validate(payload, CategoryDetail)

    async def get_categories(
        self,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> list[Category]:
        """Flat list of all categories."""
        args: dict[str, Any] = {}
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_categories", args)
        return self._validate(payload, Category, many=True)

    async def get_categories_tree(
        self,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> CategoriesTree:
        """Full category tree."""
        args: dict[str, Any] = {}
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_categories_tree", args)
        return self._validate(payload, CategoriesTree)

    async def get_product_sets(
        self,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot_start: str | None = None,
        timeslot_end: str | None = None,
    ) -> list[ProductSet]:
        """Curated product sets."""
        args: dict[str, Any] = {}
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot_start is not None:
            args["timeslotStart"] = timeslot_start
        if timeslot_end is not None:
            args["timeslotEnd"] = timeslot_end
        payload = await self.call_tool("silpo_get_product_sets", args)
        return self._validate(payload, ProductSet, many=True)

    # -- Cart (7) -----------------------------------------------------------

    async def get_cart(self) -> CartSummary:
        """Return the ID of the active cart (always the first step)."""
        payload = await self.call_tool("silpo_get_my_shopping_cart", {})
        return self._validate(payload, CartSummary)

    async def get_cart_by_id(self, cart_id: str) -> SilpoCart:
        """Return the full cart: items, delivery, slot, sums, validations."""
        payload = await self.call_tool("silpo_get_shopping_cart_by_id", {"cartId": cart_id, "shoppingCartId": cart_id})
        return self._validate(payload, SilpoCart)

    async def add_or_update_cart_products(
        self,
        cart_id: str,
        items: list[dict[str, Any]],
    ) -> CartUpdateResult:
        """Add products or update quantities in the cart.

        ``items`` entries need ``productId`` + ``companyId`` + ``branchId``
        (as returned by product search) plus a ``quantity``.
        """
        payload = await self.call_tool(
            "silpo_add_or_update_cart_products", {"cartId": cart_id, "shoppingCartId": cart_id, "items": items}
        )
        return self._validate(payload, CartUpdateResult)

    async def remove_cart_products(self, cart_id: str, product_ids: list[str]) -> CartUpdateResult:
        """Remove specific products from the cart."""
        payload = await self.call_tool(
            "silpo_remove_cart_products", {"cartId": cart_id, "shoppingCartId": cart_id, "productIds": product_ids}
        )
        return self._validate(payload, CartUpdateResult)

    async def clear_cart(self, cart_id: str) -> CartUpdateResult:
        """Clear the entire cart."""
        payload = await self.call_tool("silpo_clear_shopping_cart", {"cartId": cart_id, "shoppingCartId": cart_id})
        return self._validate(payload, CartUpdateResult)

    async def update_shopping_cart(
        self,
        cart_id: str,
        *,
        branch_id: str | None = None,
        delivery_type: str | None = None,
        timeslot: str | None = None,
        address: str | None = None,
        promo_code: str | None = None,
        coupon_code: str | None = None,
        bonus_requested: float | None = None,
    ) -> CartUpdateResult:
        """Update delivery, slot, address, promo/coupon, or apply bonuses."""
        args: dict[str, Any] = {"cartId": cart_id, "shoppingCartId": cart_id}
        if branch_id is not None:
            args["branchId"] = branch_id
        if delivery_type is not None:
            args["deliveryType"] = delivery_type
        if timeslot is not None:
            args["timeslot"] = timeslot
        if address is not None:
            args["address"] = address
        if promo_code is not None:
            args["promoCode"] = promo_code
        if coupon_code is not None:
            args["couponCode"] = coupon_code
        if bonus_requested is not None:
            args["bonusRequested"] = bonus_requested
        payload = await self.call_tool("silpo_update_shopping_cart", args)
        return self._validate(payload, CartUpdateResult)

    async def add_or_update_certificates(self, cart_id: str, certificate_ids: list[str]) -> CartUpdateResult:
        """Add or remove gift certificates from the cart."""
        payload = await self.call_tool(
            "silpo_add_or_update_certificates",
            {"cartId": cart_id, "shoppingCartId": cart_id, "certificateIds": certificate_ids},
        )
        return self._validate(payload, CartUpdateResult)

    # -- Orders (2) ---------------------------------------------------------

    async def get_online_orders(self) -> list[OnlineOrder]:
        """History of online orders."""
        payload = await self.call_tool("silpo_get_my_online_orders", {})
        return self._validate(payload, OnlineOrder, many=True)

    async def get_offline_orders(self) -> list[OfflineReceipt]:
        """History of physical-store purchases (receipts)."""
        payload = await self.call_tool("silpo_get_my_offline_orders", {})
        return self._validate(payload, OfflineReceipt, many=True)

    # -- Profile (4) --------------------------------------------------------

    async def get_profile(self) -> Profile:
        """Profile data: name, phone, email, birth date."""
        payload = await self.call_tool("silpo_get_my_profile", {})
        return self._validate(payload, Profile)

    async def get_delivery_addresses(self) -> list[DeliveryAddress]:
        """Saved delivery addresses."""
        payload = await self.call_tool("silpo_get_my_delivery_addresses", {})
        return self._validate(payload, DeliveryAddress, many=True)

    async def get_family(self) -> list[FamilyMember]:
        """Family members in the profile."""
        payload = await self.call_tool("silpo_get_my_family", {})
        return self._validate(payload, FamilyMember, many=True)

    async def get_food_restrictions(self) -> FoodRestrictions:
        """Dietary restrictions and food preferences."""
        payload = await self.call_tool("silpo_get_my_food_restrictions", {})
        return self._validate(payload, FoodRestrictions)

    # -- Loyalty & promotions (7) -------------------------------------------

    async def get_loyalty_info(self) -> LoyaltyInfo:
        """Vlasnyi Rakunok loyalty card info."""
        payload = await self.call_tool("silpo_get_loyalty_info", {})
        return self._validate(payload, LoyaltyInfo)

    async def get_coupons(self) -> list[Coupon]:
        """Available discount coupons."""
        payload = await self.call_tool("silpo_get_my_coupons", {})
        return self._validate(payload, Coupon, many=True)

    async def get_coupon_details(self, coupon_id: str) -> CouponDetail:
        """Full coupon info: conditions, products, barcode."""
        payload = await self.call_tool("silpo_get_coupon_details", {"couponId": coupon_id})
        return self._validate(payload, CouponDetail)

    async def get_promos(self) -> list[Promo]:
        """Personal promo offers."""
        payload = await self.call_tool("silpo_get_my_promos", {})
        return self._validate(payload, Promo, many=True)

    async def get_promo_codes(self) -> list[PromoCode]:
        """Active promo codes."""
        payload = await self.call_tool("silpo_get_promo_codes", {})
        return self._validate(payload, PromoCode, many=True)

    async def get_certificates(self) -> list[Certificate]:
        """Active gift certificates."""
        payload = await self.call_tool("silpo_get_my_certificates", {})
        return self._validate(payload, Certificate, many=True)

    async def get_premium_subscription(self) -> PremiumSubscription:
        """Silpo Premium subscription status."""
        payload = await self.call_tool("silpo_get_my_premium_subscription", {})
        return self._validate(payload, PremiumSubscription)
