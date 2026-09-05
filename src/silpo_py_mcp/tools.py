"""Tool name constants for the Silpo MCP server."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["SilpoTool"]


class SilpoTool(StrEnum):
    """Typed enumeration of the 40 documented ``silpo_*`` tools."""

    # Location & delivery (6)
    FIND_ADDRESS = "silpo_find_address"
    GET_AVAILABLE_DELIVERY_TYPES = "silpo_get_available_delivery_types"
    LIST_BRANCHES = "silpo_list_branches"
    GET_TIME_SLOTS = "silpo_get_time_slots"
    FIND_NOVA_POSHTA_SETTLEMENTS = "silpo_find_nova_poshta_settlements"
    FIND_NOVA_POSHTA_OFFICES = "silpo_find_nova_poshta_offices"
    # Product search (7)
    FIND_PRODUCTS_BATCH = "silpo_find_products_batch"
    GET_PRODUCTS = "silpo_get_products"
    GET_PRODUCT_DETAILS = "silpo_get_product_details"
    GET_SIMILAR_PRODUCTS = "silpo_get_similar_products"
    GET_REPLACEMENTS = "silpo_get_replacements"
    GET_MY_FAVORITES = "silpo_get_my_favorites"
    ADD_OR_UPDATE_FAVORITE_PRODUCTS = "silpo_add_or_update_favorite_products"
    # Catalog (6)
    GET_PROMOTIONS = "silpo_get_promotions"
    GET_POPULAR_CATEGORIES = "silpo_get_popular_categories"
    GET_CATEGORY = "silpo_get_category"
    GET_CATEGORIES = "silpo_get_categories"
    GET_CATEGORIES_TREE = "silpo_get_categories_tree"
    GET_PRODUCT_SETS = "silpo_get_product_sets"
    # Cart (8)
    GET_MY_SHOPPING_CART = "silpo_get_my_shopping_cart"
    CREATE_SHOPPING_CART = "silpo_create_shopping_cart"
    GET_SHOPPING_CART_BY_ID = "silpo_get_shopping_cart_by_id"
    ADD_OR_UPDATE_CART_PRODUCTS = "silpo_add_or_update_cart_products"
    REMOVE_CART_PRODUCTS = "silpo_remove_cart_products"
    CLEAR_SHOPPING_CART = "silpo_clear_shopping_cart"
    UPDATE_SHOPPING_CART = "silpo_update_shopping_cart"
    ADD_OR_UPDATE_CERTIFICATES = "silpo_add_or_update_certificates"
    # Orders (2)
    GET_MY_ONLINE_ORDERS = "silpo_get_my_online_orders"
    GET_MY_OFFLINE_ORDERS = "silpo_get_my_offline_orders"
    # Profile (4)
    GET_MY_PROFILE = "silpo_get_my_profile"
    GET_MY_DELIVERY_ADDRESSES = "silpo_get_my_delivery_addresses"
    GET_MY_FAMILY = "silpo_get_my_family"
    GET_MY_FOOD_RESTRICTIONS = "silpo_get_my_food_restrictions"
    # Loyalty & promotions (7)
    GET_LOYALTY_INFO = "silpo_get_loyalty_info"
    GET_MY_COUPONS = "silpo_get_my_coupons"
    GET_COUPON_DETAILS = "silpo_get_coupon_details"
    GET_MY_PROMOS = "silpo_get_my_promos"
    GET_PROMO_CODES = "silpo_get_promo_codes"
    GET_MY_CERTIFICATES = "silpo_get_my_certificates"
    GET_MY_PREMIUM_SUBSCRIPTION = "silpo_get_my_premium_subscription"
