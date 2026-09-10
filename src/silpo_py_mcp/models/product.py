"""Product and catalog models."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field

from silpo_py_mcp.models.base import SilpoModel


class SilpoProduct(SilpoModel):
    """A product as returned by product search tools.

    Accepts both the live shape (``id``/``name``/``available``/``image``/
    ``displayRatio``/``specialPrices``, nullable ``companyId``/``branchId``)
    and the mock/documented shape (``productId``/``title``/``isOnSale``/
    ``isPrivateLabel``/``category``).
    """

    product_id: str = Field(validation_alias=AliasChoices("productId", "id"), description="Silpo product identifier.")
    company_id: str | None = Field(default=None, alias="companyId", description="Company (supplier) identifier.")
    branch_id: str | None = Field(default=None, alias="branchId", description="Branch/store identifier.")
    title: str = Field(validation_alias=AliasChoices("title", "name"))
    slug: str | None = None
    brand: str | None = None
    price: float
    old_price: float | None = Field(default=None, alias="oldPrice")
    is_on_sale: bool = Field(default=False, alias="isOnSale")
    is_private_label: bool = Field(default=False, alias="isPrivateLabel", description="ВТМ (Премія / Повна Чаша).")
    is_available: bool = Field(default=True, validation_alias=AliasChoices("isAvailable", "available"))
    category: str | None = None
    image_url: str | None = Field(default=None, validation_alias=AliasChoices("imageUrl", "image"))
    unit: str | None = None
    stock: float | None = None
    weighted: bool | None = None
    step: float | None = None
    display_ratio: str | None = Field(default=None, alias="displayRatio")
    special_prices: list[dict[str, Any]] | None = Field(default=None, alias="specialPrices")
    external_product_id: int | None = Field(default=None, alias="externalProductId")
    extra: dict[str, Any] = Field(default_factory=dict)


class ProductDetail(SilpoModel):
    """Full product card from ``silpo_get_product_details``.

    Live shape: identity (``id``/``name``/``slug``), pricing, stock,
    ``displayRatio``/``url``/``images``/``attributes``. The legacy
    ``description``/``composition``/``nutritionalValue`` fields are kept for
    backward compatibility with older fixtures.
    """

    product_id: str | None = Field(default=None, validation_alias=AliasChoices("productId", "id"))
    company_id: str | None = Field(default=None, alias="companyId")
    branch_id: str | None = Field(default=None, alias="branchId")
    title: str | None = Field(default=None, validation_alias=AliasChoices("title", "name"))
    slug: str | None = None
    price: float | None = None
    old_price: float | None = Field(default=None, alias="oldPrice")
    stock: float | None = None
    is_available: bool | None = Field(default=None, validation_alias=AliasChoices("isAvailable", "available"))
    weighted: bool | None = None
    step: float | None = None
    ratio: str | None = None
    display_ratio: str | None = Field(default=None, alias="displayRatio")
    url: str | None = None
    images: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    composition: list[str] = Field(default_factory=list)
    nutritional_value: dict[str, Any] = Field(default_factory=dict, alias="nutritionalValue")


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

    id: str = Field(validation_alias=AliasChoices("id", "slug"))
    title: str
    description: str | None = None
    products: list[SilpoProduct] = Field(default_factory=list)
    link: str | None = None
