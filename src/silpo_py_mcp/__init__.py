"""silpo-py-mcp — typed Python client for the official Silpo MCP server.

Supports both the real ``https://mcp.silpo.ua/mcp`` endpoint (Streamable HTTP +
OAuth 2.1/PKCE) and an in-memory mock server for development and tests.

Quick start (against the mock):

    from fastmcp import Client
    from silpo_py_mcp import SilpoClient, SilpoMockServer

    server = SilpoMockServer()
    async with SilpoClient.from_fastmcp(Client(server.fastmcp)) as client:
        products = await client.get_products(
            "bran-1", "DeliveryHome", "2026-09-06T10:00:00+03:00", "2026-09-06T11:00:00+03:00"
        )

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

from importlib.metadata import PackageNotFoundError, version

from fastmcp import Client as FastMCPClient

from silpo_py_mcp import auth, config, exceptions, models, slot_time, tools
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
    CartAddressType,
    CartAmount,
    CartCalculation,
    CartDelivery,
    CartItem,
    CartLineInput,
    CartLoan,
    CartLoanConfig,
    CartLoyalty,
    CartPayment,
    CartPaymentOption,
    CartSummary,
    CartTotals,
    CartUpdatePayloads,
    CartUpdateResult,
    CartValidation,
    CategoriesTree,
    Category,
    CategoryDetail,
    CategoryNode,
    CategoryPathItem,
    CategoryPriceRange,
    Certificate,
    Coupon,
    CouponDetail,
    CouponProgress,
    CouponSuccessorThreshold,
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
    OfflineReceiptItem,
    OnlineOrder,
    OnlineOrderItem,
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
    SubscriptionFeature,
    TimeSlot,
    TimeSlotDeliveryType,
    UpdateCartDeliveryType,
)
from silpo_py_mcp.tools import SilpoTool

#: Read from the installed distribution so it cannot drift from pyproject.toml.
try:
    __version__ = version("silpo-py-mcp")
except PackageNotFoundError:  # running from a source checkout, not installed
    __version__ = "0.0.0.dev0"

__all__ = [
    "SILPO_MCP_URL",
    "Address",
    "AvailableDeliveryType",
    "BatchProductResult",
    "Branch",
    "CartAddressType",
    "CartAmount",
    "CartCalculation",
    "CartDelivery",
    "CartItem",
    "CartLineInput",
    "CartLoan",
    "CartLoanConfig",
    "CartLoyalty",
    "CartPayment",
    "CartPaymentOption",
    "CartSummary",
    "CartTotals",
    "CartUpdatePayloads",
    "CartUpdateResult",
    "CartValidation",
    "CategoriesTree",
    "Category",
    "CategoryDetail",
    "CategoryNode",
    "CategoryPathItem",
    "CategoryPriceRange",
    "Certificate",
    "Coupon",
    "CouponDetail",
    "CouponProgress",
    "CouponSuccessorThreshold",
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
    "OfflineReceiptItem",
    "OnlineOrder",
    "OnlineOrderItem",
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
    "SubscriptionFeature",
    "TimeSlot",
    "TimeSlotDeliveryType",
    "UpdateCartDeliveryType",
    "__version__",
    "auth",
    "build_encrypted_token_storage",
    "build_oauth",
    "build_settings",
    "config",
    "exceptions",
    "models",
    "slot_time",
    "tools",
]
