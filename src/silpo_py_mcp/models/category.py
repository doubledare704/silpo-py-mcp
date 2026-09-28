"""Category and promotion models."""

from __future__ import annotations

from pydantic import AliasChoices, Field

from silpo_py_mcp.models.base import SilpoModel


class CategoryPathItem(SilpoModel):
    """One ancestor of a category in ``silpo_get_category``'s breadcrumb path."""

    id: str
    slug: str
    title: str


class CategoryPriceRange(SilpoModel):
    """Price bounds of a category (``priceRange``).

    ``min`` equals ``max`` for a single-product category.
    """

    min: float = 0.0
    max: float = 0.0


class Category(SilpoModel):
    """A product category.

    ``path``/``price_range``/``visible`` are filled by
    ``silpo_get_category`` (release-1.111.3); the flat
    ``silpo_get_categories`` listing leaves them unset. ``visible is False``
    means the category has no products at the requested branch — treat it as
    unavailable rather than browsing it via ``silpo_get_products``.
    """

    id: str
    slug: str
    title: str
    parent_id: str | None = Field(default=None, alias="parentId")
    product_count: int = Field(default=0, alias="productCount")
    image_url: str | None = Field(default=None, alias="imageUrl")
    url: str | None = None
    path: list[CategoryPathItem] = Field(default_factory=list)
    price_range: CategoryPriceRange | None = Field(default=None, alias="priceRange")
    visible: bool | None = None


class CategoryNode(SilpoModel):
    """A category with its subcategories (used in the categories tree)."""

    slug: str | None = None
    total: int | None = None
    children: list[CategoryNode] = Field(default_factory=list)


class CategoriesTree(SilpoModel):
    """Full category tree."""

    root_categories: list[CategoryNode] = Field(alias="rootCategories")


class CategoryDetail(SilpoModel):
    """Details of a single category, from ``silpo_get_category``.

    **Breaking in release-1.111.3:** the tool no longer returns child
    categories — the upstream API never includes them for this endpoint — so
    ``subcategories`` (fed by a ``children`` key) is gone. Use
    ``silpo_get_categories_tree`` to discover child categories instead.
    ``category`` itself now carries the ancestor ``path``, the ``price_range``
    and the ``visible`` flag.
    """

    category: Category

    @property
    def path(self) -> list[CategoryPathItem]:
        """Ancestor breadcrumb, root first, category itself last."""
        return self.category.path

    @property
    def price_range(self) -> CategoryPriceRange | None:
        return self.category.price_range

    @property
    def is_visible(self) -> bool | None:
        """``False`` means no products at the requested branch."""
        return self.category.visible

    @property
    def has_products(self) -> bool:
        """``True`` unless the server explicitly flagged the category invisible."""
        return self.category.visible is not False


class Promotion(SilpoModel):
    """An active promotion / discount."""

    id: str = Field(validation_alias=AliasChoices("id", "code"))
    title: str
    description: str | None = None
    product_count: int | None = Field(default=None, alias="productCount")
    url: str | None = None
    discount_percent: float | None = Field(default=None, alias="discountPercent")
    price_from: float | None = Field(default=None, alias="priceFrom")
    price_to: float | None = Field(default=None, alias="priceTo")
    starts_at: str | None = Field(default=None, alias="startsAt")
    ends_at: str | None = Field(default=None, alias="endsAt")
    is_price_of_week: bool = Field(default=False, alias="isPriceOfWeek")
    image_url: str | None = Field(default=None, alias="imageUrl")
