"""Category and promotion models."""

from __future__ import annotations

from pydantic import Field

from silpo_mcp.models.base import SilpoModel


class Category(SilpoModel):
    """A product category."""

    id: str
    slug: str
    title: str
    parent_id: str | None = Field(default=None, alias="parentId")
    product_count: int = Field(default=0, alias="productCount")
    image_url: str | None = Field(default=None, alias="imageUrl")


class CategoryNode(SilpoModel):
    """A category with its subcategories (used in the categories tree)."""

    children: list[CategoryNode] = Field(default_factory=list)


class CategoriesTree(SilpoModel):
    """Full category tree."""

    root_categories: list[CategoryNode] = Field(alias="rootCategories")


class CategoryDetail(SilpoModel):
    """Details of a single category: subcategories and product counts."""

    category: Category
    subcategories: list[Category] = Field(default_factory=list)


class Promotion(SilpoModel):
    """An active promotion / discount."""

    id: str
    title: str
    description: str | None = None
    discount_percent: float | None = Field(default=None, alias="discountPercent")
    price_from: float | None = Field(default=None, alias="priceFrom")
    price_to: float | None = Field(default=None, alias="priceTo")
    starts_at: str | None = Field(default=None, alias="startsAt")
    ends_at: str | None = Field(default=None, alias="endsAt")
    is_price_of_week: bool = Field(default=False, alias="isPriceOfWeek")
    image_url: str | None = Field(default=None, alias="imageUrl")
