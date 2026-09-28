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

    ``display_price`` (release-1.110.1) is the per-display-unit price the
    server filters ``fromPrice``/``toPrice`` by — it equals ``price`` for
    unit-counted products but can differ significantly for weighted ones
    (e.g. ``price=88.11``/``displayPrice=8.81``). When a guest states a
    budget in real money, filter the returned products by ``price``
    yourself rather than relying on ``fromPrice``/``toPrice``, which are
    applied to ``display_price`` and so misjudge weighted items.

    ``weighted``/``step``/``display_ratio`` (release-1.111.3): for
    ``weighted=True`` products ``step`` and the ``quantity`` sent to
    ``add_or_update_cart_products`` are **always kilograms**, whatever unit
    ``display_ratio`` shows (``display_ratio="100г"`` with ``step=0.35``
    still means 350 g). ``display_ratio`` only describes one unit for
    display/pricing; it is never a conversion factor for ``step``.
    """

    product_id: str = Field(validation_alias=AliasChoices("productId", "id"), description="Silpo product identifier.")
    company_id: str | None = Field(default=None, alias="companyId", description="Company (supplier) identifier.")
    branch_id: str | None = Field(default=None, alias="branchId", description="Branch/store identifier.")
    title: str = Field(validation_alias=AliasChoices("title", "name"))
    slug: str | None = None
    brand: str | None = None
    price: float
    display_price: float | None = Field(default=None, validation_alias=AliasChoices("displayPrice", "display_price"))
    old_price: float | None = Field(default=None, alias="oldPrice")
    is_on_sale: bool = Field(default=False, alias="isOnSale")
    is_private_label: bool = Field(default=False, alias="isPrivateLabel", description="ВТМ (Премія / Повна Чаша).")
    is_available: bool = Field(default=True, validation_alias=AliasChoices("isAvailable", "available"))
    has_offer_at_branch: bool | None = Field(
        default=None,
        alias="hasOfferAtBranch",
        description="release-1.110.0: False when the product has no real offer at the requested branch.",
    )
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

    Live shape: identity (``id``/``name``/``slug``), pricing (``price``/
    ``displayPrice``), stock, ``displayRatio``/``url``/``image``/``images``/
    ``attributes``. ``weighted`` is derived server-side from ``ratio``
    (``"кг"`` = weighted) when the upstream API omits the flag. The legacy
    ``description``/``composition``/``nutritionalValue`` fields are kept for
    backward compatibility with older fixtures.

    Since server release-1.110.0 ``price``/``displayPrice``/``stock``/
    ``available`` are the requested branch's real offer — not catalog-wide
    data — and ``has_offer_at_branch`` explicitly signals whether such an
    offer exists. Always check it first: when ``False`` the product has no
    real offer at that branch (mock returns ``stock=0``/``available=False``
    with the catalog price for reference).

    This card is for product information, not for final ordering decisions —
    confirm price and availability through ``find_products_batch`` or the
    cart before telling the guest what they will pay (release-1.111.3).
    ``image`` is a single thumbnail while ``images`` is the full gallery
    (it may repeat ``image`` plus extras); prefer ``images`` for a detail
    view. For ``weighted`` products ``step`` is always in kilograms.
    """

    product_id: str | None = Field(default=None, validation_alias=AliasChoices("productId", "id"))
    company_id: str | None = Field(default=None, alias="companyId")
    branch_id: str | None = Field(default=None, alias="branchId")
    title: str | None = Field(default=None, validation_alias=AliasChoices("title", "name"))
    slug: str | None = None
    price: float | None = None
    display_price: float | None = Field(default=None, validation_alias=AliasChoices("displayPrice", "display_price"))
    old_price: float | None = Field(default=None, alias="oldPrice")
    stock: float | None = None
    is_available: bool | None = Field(default=None, validation_alias=AliasChoices("isAvailable", "available"))
    has_offer_at_branch: bool | None = Field(default=None, alias="hasOfferAtBranch")
    weighted: bool | None = None
    step: float | None = None
    ratio: str | None = None
    display_ratio: str | None = Field(default=None, alias="displayRatio")
    url: str | None = None
    image: str | None = None
    images: list[str] = Field(default_factory=list)
    special_prices: list[dict[str, Any]] | None = Field(default=None, alias="specialPrices")
    external_product_id: int | None = Field(default=None, alias="externalProductId")
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
    """Result of ``silpo_find_products_batch``: query -> matches.

    ``dropped_count`` mirrors the live ``meta.droppedCount`` — the number of
    empty/whitespace-only entries the server skipped rather than searched
    (release-1.110.1 never errors on those; all-empty input returns
    ``success:true`` with an empty ``queries`` array).

    ``total_found`` maps each query to the live ``queries[].totalFound`` — the
    real number of matches, which exceeds ``results[query]`` whenever
    ``limit`` cut the list short (release-1.111.3). Re-query with a higher
    ``limit`` instead of concluding a product does not exist when it is
    missing from ``results``: a zero-stock product can be absent even when
    searched by its exact article code.
    """

    results: dict[str, list[SilpoProduct]]
    unmatched: list[str] = Field(default_factory=list)
    dropped_count: int = Field(default=0, alias="droppedCount")
    total_found: dict[str, int] = Field(default_factory=dict, alias="totalFound")

    @property
    def truncated_queries(self) -> list[str]:
        """Queries whose real match count exceeded the returned products."""
        return [query for query, count in self.total_found.items() if count > len(self.results.get(query, []))]

    def is_truncated(self, query: str) -> bool:
        """Whether ``query`` had more matches than were returned."""
        return self.total_found.get(query, 0) > len(self.results.get(query, []))


class ProductSet(SilpoModel):
    """A curated selection of products (thematic, seasonal)."""

    id: str = Field(validation_alias=AliasChoices("id", "slug"))
    title: str
    description: str | None = None
    products: list[SilpoProduct] = Field(default_factory=list)
    link: str | None = None
