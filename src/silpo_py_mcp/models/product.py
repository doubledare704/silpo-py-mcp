"""Product and catalog models."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from silpo_py_mcp.models.base import SilpoModel


class SilpoProduct(SilpoModel):
    """A product as returned by product search tools."""

    product_id: str = Field(alias="productId", description="Silpo product identifier.")
    company_id: str = Field(alias="companyId", description="Company (supplier) identifier.")
    branch_id: str = Field(alias="branchId", description="Branch/store identifier.")
    title: str
    slug: str | None = None
    brand: str | None = None
    price: float
    old_price: float | None = Field(default=None, alias="oldPrice")
    is_on_sale: bool = Field(default=False, alias="isOnSale")
    is_private_label: bool = Field(default=False, alias="isPrivateLabel", description="ВТМ (Премія / Повна Чаша).")
    is_available: bool = Field(default=True, alias="isAvailable")
    category: str | None = None
    image_url: str | None = Field(default=None, alias="imageUrl")
    unit: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ProductDetail(SilpoModel):
    """Full product card: composition, nutritional value, attributes."""

    description: str | None = None
    composition: list[str] = Field(default_factory=list)
    nutritional_value: dict[str, Any] = Field(default_factory=dict, alias="nutritionalValue")
    attributes: dict[str, Any] = Field(default_factory=dict)


class ProductSearchResult(SilpoModel):
    """Paginated product listing."""

    items: list[SilpoProduct]
    total: int
    page: int = 1
    page_size: int = Field(default=20, alias="pageSize")
    has_more: bool = Field(default=False, alias="hasMore")


class ProductBatchItem(SilpoModel):
    """A single requested item in ``silpo_find_products_batch``."""

    query: str
    limit: int = 1


class ProductMatch(SilpoModel):
    """A product match with the query that produced it."""

    query: str


class BatchProductResult(SilpoModel):
    """Result of ``silpo_find_products_batch``: query -> matches."""

    results: dict[str, list[SilpoProduct]]
    unmatched: list[str] = Field(default_factory=list)


class ProductSet(SilpoModel):
    """A curated selection of products (thematic, seasonal)."""

    id: str
    title: str
    description: str | None = None
    products: list[SilpoProduct] = Field(default_factory=list)
