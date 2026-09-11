# Changelog

## 0.5.0 — 2026-09-11

Reconciled with server release-1.110.1 and re-verified all 40 tools against
the live `tools/list` schemas plus live responses with real data. No drift in
tool names except the one breaking change below; no new tools.

This is a **breaking release**: `get_similar_products` now requires the
delivery timeslot.

### Added

- `SilpoProduct.display_price` (`displayPrice`) on every product-returning
  tool (`find_products_batch`, `get_products`, `get_similar_products`,
  `get_replacements`); `fromPrice`/`toPrice` filter by it, not by `price`.
- `ProductDetail` now exposes the release-1.110.1 fields `displayPrice`,
  `image` (thumbnail alongside `images`), `specialPrices` and
  `externalProductId`.
- `BatchProductResult.dropped_count` mirrors the live `meta.droppedCount`
  (empty/whitespace-only batch entries are skipped, never an error).
- Mock `silpo_find_products_batch` returns the live shape (`queries[]` with
  `totalFound` + `meta` with `totalQueries`/`totalProducts`/`droppedCount`)
  and matches numeric article codes (`externalProductId`) like the server.

### Changed (breaking)

- `get_similar_products` takes `delivery_type`/`timeslot_start`/`timeslot_end`
  as required positional args (live schema now requires them for accurate
  stock); the mock tool requires them too. Calls without a timeslot now fail
  server-side with `-32602`.
- `get_products` docstring documents the upstream (non-fixable) sort-ordering:
  in-stock before out-of-stock, and within each group unit-counted before
  weighted regardless of `sortDirection`; plus the `displayPrice` vs `price`
  distinction for `fromPrice`/`toPrice`.
- Mock `silpo_get_products` price filters compare `displayPrice` (falling back
  to `price`), matching the fixed server behavior.

### Fixed

- `get_favorites` unwraps the live `{success, summary, products, meta}`
  envelope (previously only the mock's bare list validated).
- Mock `silpo_get_product_details` returns the full live product card
  (`displayPrice`, `image`, `specialPrices`, `externalProductId`, correct
  `weighted`).

## 0.4.0 — 2026-09-10

Reconciled with server release-1.110.0 and re-verified all 40 tools against
the live `tools/list` schemas plus live responses with real data. No drift in
tool names, argument names or required sets; the release's `get-products`
change is description-only (sort-order and package-size guidance, no schema
change — the client docstring now mentions the `inStock: true` trick).

This is a **breaking release**: several Pydantic models are remodeled from
the documented shapes to the live shapes, and two typed-method signatures
changed.

### Added

- `CouponDetail` now exposes the release-1.110.0 `canBeAppliedToOrder`
  eligibility flag plus `state`, `usedCount`, reward fields (`rewardText`/
  `rewardValue`/`rewardUnit`/`rewardSign`/`rewardLimit`), `promoId`,
  `limitText`/`warningText` and `progress` (`CouponProgress`), with
  `business_coupon_id` auto-filled from the live numeric `id`.
- Live fields across product/catalog models: `displayRatio`/
  `specialPrices` on `SilpoProduct`; `ProductDetail` identity, pricing,
  `url`/`images`/`attributes`; `url` on `Category`; live `children` on
  `get_category` map onto `subcategories`.
- Live loyalty shapes: `Coupon` reward/limit fields, `Promo`
  (`selected`, reward/limit/warning text), `PromoCode` (`id`/`title`/
  `active`), `Certificate` (`totalPrice`/`pincode`/`expireDate`/`title`),
  `PremiumSubscription` (`status`, `dateFrom`/`dateTo`, `features`,
  share links).
- Live order shapes: `OnlineOrder` (`amount`, `delivery`, `address`,
  `products`) and `OfflineReceipt` (`filId`/`filialName`/`sumReg`,
  `rewards`, `products`); `DeliveryAddress` (`floor`/`entrance`/
  `latitude`/`longitude`/`comment`); `FamilyMember`
  (`image`/`profileCreatedAt`); `Profile.id`.
- `DeliveryType` covers all 16 live enum values (was 5).
- `get_certificates` accepts `limit`/`offset`.

### Changed (breaking)

- `CouponDetail`/`Coupon`/`Promo`/`PromoCode`/`Certificate`/
  `PremiumSubscription`/`OnlineOrder`/`OfflineReceipt`/`ProductDetail` follow
  the live field names; mock fixtures return the live shapes and tests assert
  them (e.g. `total_price` instead of `nominal` for certificates).
- `add_or_update_certificates` takes `list[str | dict]` and sends
  `certificatesToAdd` as `[{barcode, pincode?}]` objects per the live schema
  (plain strings are converted automatically).
- `get_coupon_details` takes `business_coupon_id: int | float | str`.
- Cart mutations (`add`/`remove`/`clear`/`update`/`certificates`) return the
  live `success`/`summary`/`products`/`added`/`removed` fields on
  `CartUpdateResult`; the live server does not echo the full cart, so call
  `get_cart_by_id` afterwards (as the server itself mandates).
- `get_cart_by_id` maps the live nesting onto `SilpoCart`: `branchId` from
  `shipments[0]`, sums from `calculation`, `validations` from
  `calculation.validations` (live `{level, type, message, context}` shape),
  plus top-level `loyalty`/checkout links.

### Fixed

- `_unwrap_payload` now unwraps dict-valued envelopes (`profile`,
  `loyalty`, `coupon`, `cart`) — previously `get_profile`,
  `get_loyalty_info` and `get_coupon_details` validated but returned empty
  objects against the live server.
- `SilpoProduct.company_id`/`branch_id` accept `null` (live schema); `null`
  `Address.address` no longer fails validation.
- `TimeSlot.fast` accepts the live `{cost, time}` object; `NovaPoshtaOffice`
  captures top-level `latitude`/`longitude`.

## 0.3.1 — 2026-09-07

Re-verified all 40 tools against the live `tools/list` schemas and live
response shapes (fresh OAuth run, Sep 7 2026). No drift in tool names and no
typed-method input changes needed: every typed method except the known
server-buggy `get_favorites` validated its live response through the current
Pydantic models (29/30 passed; `silpo_get_my_favorites` still fails server-side
with a corrupted-entry `null` id).

### Fixed

- Mock `silpo_get_shopping_cart_by_id` and `silpo_clear_shopping_cart` now
  require only `shoppingCartId` — the legacy optional `cartId` alias (not
  present in the live schema) was removed, matching the other cart tools.
- Mock `silpo_add_or_update_certificates` accepts optional
  `certificatesToAdd`/`certificatesToRemove` arrays like the live schema
  (they are no longer mandatory arguments).

## 0.3.0 — 2026-09-06

Full reconciliation of every typed method and mock tool with the live
`tools/list` schemas, and of every Pydantic model with the live response
shapes (both dumped from the real server after OAuth login). This is a
**breaking release**: signatures changed for the methods below.

### Changed (breaking)

- Context args are now required where the live schema requires them:
  `get_products`, `get_promotions`, `get_categories_tree`, `get_offline_orders`
  take `branch_id`/`delivery_type`/`timeslot_start`/`timeslot_end`;
  `get_product_details` takes `branch_id`/`slug`/`delivery_type`/
  `timeslot_start`/`timeslot_end` (was `product_id`); `get_category` takes
  `branch_id`/`delivery_type`/`category_slug`; `get_popular_categories` takes
  `branch_id`/`delivery_type`; `get_categories` and `get_product_sets` take
  `branch_id`; `get_favorites` takes `branch_id`/`delivery_type`/
  `timeslot_start`; `get_replacements` takes `branch_id`/`company_id`/
  `delivery_type`; `get_similar_products` takes `branch_id`/`slug`.
- `get_products` filters follow the live schema: `category`, `promotionCode`,
  `inStock`, `mustHavePromotion`, `set`, `sortBy`, `sortDirection`, `fromPrice`,
  `toPrice`, `limit`, `offset` (removed `query`, `categoryId`, `onSale`,
  `page`, `pageSize` — use `find_products_batch` for free-text search).
- `find_products_batch` takes `branch_id`/`delivery_type`/`timeslot_start`/
  `timeslot_end`/`queries` and sends `products` as a list of strings.
- `update_favorites` takes `actions` (`[{productId, externalProductId,
  toDelete}]`) instead of `product_ids`/`add`.
- `update_shopping_cart` requires `delivery_type`, `timeslot` (dict),
  `address` (dict) and `shipments`; `coupon_code` was removed (live schema has
  `promoCode` only); added `feedback_changes`/`feedback_contacts`/
  `is_adult_confirmed`.
- `get_coupon_details` takes `business_coupon_id` (was `coupon_id`).
- `find_nova_poshta_settlements` sends `title`; `find_address` sends `address`;
  `get_time_slots` sends `deliveryTypes` (+ optional `limit`/`start`/`end`);
  cart tools send only `shoppingCartId` (dead `cartId` key dropped).
- `get_online_orders`/`get_offline_orders` accept `limit`/`offset` (+ date
  range for offline).

### Fixed

- Mock tools now expose exactly the live argument names (legacy aliases
  removed); `silpo_find_products_batch` treats `products` as a list of strings.

### Added (response-side)

- Typed methods unwrap the live `{success, summary, <data>, meta?}` envelope
  (`_unwrap_payload`) and models accept the live field names (`id`/`name`/
  `start`/`end`/`deliveryType`/`available`) alongside the documented ones via
  `AliasChoices`, so both the real server and the mock validate. Cart
  mutation responses, the category tree, batch search (`queries` → `results`)
  and `get_products` (`products` + `meta.total`) are normalized client-side.
  Verified live: 37/38 typed methods validate; `silpo_get_my_favorites`
  remains a known server-side bug (null `id` in a corrupted favorites entry).

## 0.2.2 — 2026-09-06

Reconciles the cart mutation tools with the verified live server schemas
(the real `tools/list` schemas differ from the documented ones; the live server
ignores unknown keys and fails with e.g. `expected array, received undefined at
path: ["products"]` when a renamed payload key is missing).

### Fixed

- `silpo_add_or_update_cart_products` now sends `shoppingCartId` + `products`
  instead of the legacy `cartId`/`items` keys.
- `silpo_remove_cart_products` now sends `products: [{productId}]` instead of
  the legacy `productIds` array.
- `silpo_add_or_update_certificates` now sends `certificatesToAdd` /
  `certificatesToRemove` instead of the legacy `certificateIds`.
- The mock server tools now expose exactly the live signatures for these three
  tools (legacy aliases removed).

### Changed

- Typed `SilpoClient.add_or_update_cart_products` parameter renamed
  `items` → `products` (positional callers are unaffected).