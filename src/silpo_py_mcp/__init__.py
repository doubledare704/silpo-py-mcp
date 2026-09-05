"""silpo-py-mcp — typed Python client for the official Silpo MCP server.

Supports both the real ``https://mcp.silpo.ua/mcp`` endpoint (Streamable HTTP +
OAuth 2.1/PKCE) and an in-memory mock server for development and tests.

Quick start (against the mock):

    from fastmcp import Client
    from silpo_py_mcp import SilpoClient, SilpoMockServer

    server = SilpoMockServer()
    async with SilpoClient.from_fastmcp(Client(server.fastmcp)) as client:
        products = await client.get_products(query="сир")

Quick start (against the real server):

    from fastmcp import Client
    from fastmcp.client.auth import OAuth
    from silpo_py_mcp import SilpoClient
    from silpo_py_mcp.auth import build_encrypted_token_storage
    from silpo_py_mcp.config import SilpoSettings

    settings = SilpoSettings()
    storage = build_encrypted_token_storage(settings.oauth_storage_dir)
    client = SilpoClient.from_fastmcp(
        Client(settings.mcp_url, auth=OAuth(token_storage=storage)),
    )
"""

from __future__ import annotations

from fastmcp import Client as FastMCPClient

from silpo_py_mcp import auth, config, exceptions, models, tools
from silpo_py_mcp.auth import (
    SilpoOAuthError,
    build_encrypted_token_storage,
    build_oauth,
)
from silpo_py_mcp.client import SilpoClient
from silpo_py_mcp.config import SILPO_MCP_URL, SilpoSettings, build_settings
from silpo_py_mcp.exceptions import (
    SilpoAuthError,
    SilpoConnectionError,
    SilpoError,
    SilpoForbiddenError,
    SilpoRateLimitError,
    SilpoToolExecutionError,
    SilpoToolNotFoundError,
    SilpoValidationError,
)
from silpo_py_mcp.mock_server import SilpoMockServer
from silpo_py_mcp.models import (
    Address,
    AvailableDeliveryType,
    BatchProductResult,
    Branch,
    CartItem,
    CartLineInput,
    CartLoyalty,
    CartSummary,
    CartTotals,
    CartUpdateResult,
    CartValidation,
    CategoriesTree,
    Category,
    CategoryDetail,
    CategoryNode,
    Certificate,
    Coupon,
    CouponDetail,
    CreateShoppingCartResult,
    DeliveryAddress,
    DeliveryType,
    FamilyMember,
    FoodRestrictions,
    GeoPoint,
    LoyaltyInfo,
    NovaPoshtaOffice,
    NovaPoshtaSettlement,
    OfflineReceipt,
    OnlineOrder,
    OrderLine,
    PremiumSubscription,
    ProductBatchItem,
    ProductDetail,
    ProductMatch,
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

__version__ = "0.2.1"

__all__ = [
    "SILPO_MCP_URL",
    "Address",
    "AvailableDeliveryType",
    "BatchProductResult",
    "Branch",
    "CartItem",
    "CartLineInput",
    "CartLoyalty",
    "CartSummary",
    "CartTotals",
    "CartUpdateResult",
    "CartValidation",
    "CategoriesTree",
    "Category",
    "CategoryDetail",
    "CategoryNode",
    "Certificate",
    "Coupon",
    "CouponDetail",
    "CreateShoppingCartResult",
    "DeliveryAddress",
    "DeliveryType",
    "FamilyMember",
    "FastMCPClient",
    "FoodRestrictions",
    "GeoPoint",
    "LoyaltyInfo",
    "NovaPoshtaOffice",
    "NovaPoshtaSettlement",
    "OfflineReceipt",
    "OnlineOrder",
    "OrderLine",
    "PremiumSubscription",
    "ProductBatchItem",
    "ProductDetail",
    "ProductMatch",
    "ProductSearchResult",
    "ProductSet",
    "Profile",
    "Promo",
    "PromoCode",
    "Promotion",
    "SilpoAuthError",
    "SilpoCart",
    "SilpoClient",
    "SilpoConnectionError",
    "SilpoError",
    "SilpoForbiddenError",
    "SilpoMockServer",
    "SilpoModel",
    "SilpoOAuthError",
    "SilpoProduct",
    "SilpoRateLimitError",
    "SilpoSettings",
    "SilpoTool",
    "SilpoToolExecutionError",
    "SilpoToolNotFoundError",
    "SilpoValidationError",
    "TimeSlot",
    "__version__",
    "auth",
    "build_encrypted_token_storage",
    "build_oauth",
    "build_settings",
    "config",
    "exceptions",
    "models",
    "tools",
]
