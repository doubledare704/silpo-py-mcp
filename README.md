# silpo-py-mcp [![PyPI](https://img.shields.io/pypi/v/silpo-py-mcp)](https://pypi.org/project/silpo-py-mcp/) [![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://pypi.org/project/silpo-py-mcp/)

Typed Python client for the official **Silpo** MCP server
([`https://mcp.silpo.ua/mcp`](https://ai-factory.silpo.ua/docs/mcp)).

Built on [FastMCP `3.4.7`](https://gofastmcp.com/) for the *Silpo AI Factory*
hackathon. One library, two modes:

- **Real server** — Streamable HTTP transport with OAuth 2.1 + PKCE, encrypted
  on-disk token storage, 40 typed methods mirroring the documented
  `silpo_*` tools.
- **In-memory mock** — a FastMCP server that implements the same 40 tools with
  realistic fixtures, so you can develop and test without a Silpo account.

Requires **Python 3.12+**.

---

## Install

```bash
pip install silpo-py-mcp
# or with uv
uv add silpo-py-mcp
# local development
uv sync
```

## Quick start (mock — no auth needed)

```python
import asyncio
from silpo_py_mcp import SilpoClient


async def main() -> None:
    async with SilpoClient.for_mock() as client:
        result = await client.get_products(
            "bran-1",
            "DeliveryHome",
            "2026-09-06T10:00:00+03:00",
            "2026-09-06T11:00:00+03:00",
            category="Молочні продукти",
        )
        for product in result.items:
            print(product.title, product.price)

        cart = await client.get_cart()
        await client.add_or_update_cart_products(
            cart.cart_id,
            [
                {
                    "productId": product.product_id,
                    "companyId": product.company_id,
                    "branchId": product.branch_id,
                    "quantity": 2,
                }
                for product in result.items
            ],
        )
        full = await client.get_cart_by_id(cart.cart_id)
        print("Total:", full.totals.total_price)


asyncio.run(main())
```

## Quick start (real server)

The first connection opens a browser for login at `auth.silpo.ua`
(phone + OTP or password). Tokens are encrypted and stored on disk, and the
client refreshes them automatically.

```python
import asyncio
from silpo_py_mcp import SilpoClient


async def main() -> None:
    async with SilpoClient.for_real_server() as client:
        tools = await client.list_tools()
        print(f"Connected. {len(tools)} tools available.")

        branches = await client.call_tool("silpo_list_branches", {"limit": 1})
        print("Branch:", branches["branches"][0]["address"])


asyncio.run(main())
```

> **Note on typed methods vs the real server.** The typed methods and the mock
> mirror the live `tools/list` schemas and response shapes (verified Sep 2026;
> re-verified Sep 7 2026; reconciled with server release-1.110.0 on Sep 10
> 2026; reconciled with server release-1.110.1 on Sep 11 2026;
> re-verified Sep 14 2026 — still 40 tools, no renames, no required-set
> changes; reconciled with server release-1.111.0/1.111.1 on Sep 25 2026 —
> still 40 tools, no renames; reconciled with server release-1.111.2 on
> Sep 28 2026 — still 40 tools, no renames; reconciled with server
> release-1.111.3 on Sep 28 2026 — still 40 tools, no renames, no required-set
> changes, with the cart/payment/category changes below; reconciled with
> server release-1.111.4 on Sep 30 2026 — still 40 tools, no renames, no
> required-set changes, with the promotions/time-slots/cart-description
> fixes below). Context
> arguments such as
> `branchId`/`deliveryType`/`timeslotStart`/`timeslotEnd` are required where
> the live schema requires them — since 1.110.1 this includes
> `silpo_get_similar_products` — cart tools take `shoppingCartId`, and
> `silpo_add_or_update_cart_products` takes `products`
> (`[{productId, companyId, branchId, quantity, addQuantity?, comment?}]` —
> omitted/false `addQuantity` replaces the quantity, `true` adds to it).
> `silpo_add_or_update_certificates` takes `certificatesToAdd`/
> `certificatesToRemove` as `[{barcode, pincode?}]` objects (plain barcode
> strings are converted automatically). Product results carry `displayPrice`
> (`fromPrice`/`toPrice` filter by it, not by `price`);
> `get_products` requires at least one of `category`/`mustHavePromotion`/
> `promotionCode`/`set` (release-1.111.0: missing filter raises `ValueError`
> client-side with the accepted-filter list; `timeslotStart`/`timeslotEnd`
> are not validated server-side — a bogus slot silently returns the full
> catalog, so pass a real slot from `get_time_slots`);
> `get_time_slots` sends `deliveryTypes` (singular `deliveryType` accepted
> server-side as an alias since 1.111.0; millisecond timestamps stripped
> since 1.111.1) and each slot carries `serviceFee` (SelfPickup "Сервісний
> збір"); since release-1.111.2 the server normalizes timeslot bounds
> (`Z`, `+00:00` and naive stamps are all read as UTC, date-only values are
> rejected) and restricts `deliveryTypes` to the 9-value
> `TimeSlotDeliveryType` enum — `get_time_slots` validates the types, the
> `limit` bounds (1..100) and the timestamp format client-side instead of
> letting the server answer `-32602`/400; release-1.111.4 makes the date
> normalizer more lenient (whitespace, lowercase `z`, comma fractions,
> `+HHMM`/`+HH` offsets and a space separator are read as UTC) and adds a
> `total` to the slots response (`{success, summary, slots, total}` — the
> client returns the list and ignores the count); `get_promotions` for an
> unknown branch returns `[]` instead of the pre-1.111.4 `500`;
> `find_address` surfaces `warning`/`houseNumberMatched` for
> unmatched house numbers (release-1.111.1 — check before relying on
> coordinates); `get_available_delivery_types` coordinates are only validated
> for home-delivery types (`SelfPickup`/`NovaPoshta` always returned);
> `get_product_details` carries `displayPrice`/`image`/`specialPrices`/
> `externalProductId` plus `hasOfferAtBranch` (release-1.110.0: `price`/
> `displayPrice`/`stock`/`available` are the requested branch's real offer —
> check `has_offer_at_branch` first, `False` means no real offer at that
> branch); `get_cart_by_id` maps `serviceFee` from the top level or
> `calculation` (release-1.111.1); batch empty entries are skipped
> (`meta.droppedCount` → `BatchProductResult.dropped_count`) and
> `queries[].totalFound` surfaces as `BatchProductResult.total_found`
> (`truncated_queries` flags queries whose real match count exceeded the
> returned products). Coupon
> eligibility comes from
> `canBeAppliedToOrder` on `silpo_get_coupon_details` — never infer it from
> `active`/`state` alone. The mock cart tools
> (`silpo_get_shopping_cart_by_id`, `silpo_clear_shopping_cart`, ...) accept
> **only** `shoppingCartId` — the legacy `cartId` alias was removed in 0.3.1
> to match the live schema. `call_tool` always passes arguments through
> verbatim for one-off calls. Responses come back JSON-like (nested FastMCP
> `Root` dataclasses are unwrapped automatically).

### release-1.111.3 (client 0.8.0) — breaking

| Change | Detail |
|---|---|
| `silpo_get_category` dropped `children` | The upstream API never returns child categories for this endpoint. **`CategoryDetail.subcategories` is removed.** Use `get_categories_tree` to discover children. The response now carries the ancestor `path`, a `priceRange` and a `visible` flag (`False` = no products at this branch) — exposed as `detail.path`, `detail.price_range` and `detail.is_visible`. |
| Cart payment methods | `get_cart_by_id` now parses `calculation.payment` into `CartPayment`: `payment.available_types` lists every usable method (with `payment.loan`/`loan_config` for BNPL) and `payment.unavailable_types` the blocked ones. `cart.payment_type` is only the *selected* method and stays `"Unknown"` until the guest picks one at checkout — do not read it as the list of options. |
| Cart delivery discount | `calculation.delivery` is exposed as `cart.delivery` with `sub_total`/`sub_discount` (so `sub_total - sub_discount == total`, plus `discount_percent`) and mirrored on `cart.totals.delivery_sub_total`/`delivery_discount`. The reason for a discount is *not* reported — order-total tiers and premium-subscription perks can each cause it. |
| Amount to show the guest | `calculation.total` is the total *before* discounts; `cart.total_to_pay` (`calculation.totalAfterDiscounts`) is what the guest actually pays. Always present the latter. |
| `update_shopping_cart` schema | `address` must carry an `addressType` (`CartAddressType`: `house`/`flat`/`office`/`point`/`self-pickup`/`nova-poshta`) and each `shipments` entry a `companyId` + `branchId` pair; `deliveryType` is narrowed to the 8-value `UpdateCartDeliveryType`. `update_shopping_cart` validates all of this client-side and raises `ValueError` naming the offending argument. Copy both objects from the cart via `cart.update_payloads` (`address`/`shipments`/`timeslot`/`missing_fields`) instead of building them. `clear_bonus=True` sends the explicit `bonusRequested: null` that removes bonus payment. |
| `get_time_slots` / product docs clarified | Slot times are UTC; `available` is authoritative (a type can show pricing while every slot is unavailable — filter on `TimeSlot.is_bookable`); `minOrderCost` is reported only by this tool; `serviceFee` is a preview that `calculation.serviceFee.total` supersedes once a cart exists. For `weighted=True` products `step` and cart `quantity` are **always kilograms**, whatever `display_ratio` shows. |

### release-1.111.4 (client 0.8.1)

| Change | Detail |
|---|---|
| `get-promotions` 500 fix | An unknown `branchId` returns `[]` instead of the previous `500` error — the mock mirrors it and `get_promotions` documents the empty-means-no-promotions contract. |
| `get-time-slots` date normalizer | More lenient: surrounding whitespace, lowercase `z`, comma fractions, `+HHMM`/`+HH` offsets and a space separator are all accepted and read as UTC (`silpo_py_mcp.slot_time`, shared by the client and the mock). Date-only/unparseable values still fail fast (`ValueError` client-side, `400` on the wire). |
| `get-time-slots` total response | The live response now carries `total` alongside `slots`; `get_time_slots` unwraps `slots`/`timeSlots`/`deliveryTimeSlots` and ignores the count (it always equals `len(slots)`). |
| `add-or-update-cart-products` description | Clarified tool description (full line shape, replace-vs-add, kilograms for weighted products, `get_cart_by_id` afterwards) — behavior unchanged; client and mock docstrings carry it. |

### Smoke test against the real server

`examples/real_smoke.py` verifies the live contract and runs a read-only
battery of calls:

```bash
uv run examples/real_smoke.py
```

On the first run a browser opens for login at `auth.silpo.ua`; afterwards the
encrypted token in `~/.silpo_py_mcp` is reused. The script checks:

- live `tools/list` matches the 40 documented tools and prints every live
  signature (arg names/types),
- a read-only battery of `call_tool` calls built from the live schemas
  (branches, address, delivery types, time slots, categories tree, promotions,
  products, profile, favorites, loyalty, coupons, orders, promos, certificates).

Failures are reported per check without aborting — server-side schema bugs and
drift between the real server and the mock show up as `✗` lines. Exits
non-zero if the tool-name contract is violated or a battery call fails.

### Known server-side quirks (re-verified live, Sep 2026 — mitigated in `examples/real_smoke.py`)

| Tool | Symptom | Mitigation |
|---|---|---|
| `silpo_get_products` | `400 Bad Request` on plain `limit` without filter (pre-1.111.0; now a clear message listing `category`/`mustHavePromotion`/`promotionCode`/`set`) | smoke uses `category` or `set: klatsniznyzhky`; typed `get_products` raises `ValueError` before the request |
| `silpo_get_products` | bogus `timeslotStart`/`timeslotEnd` silently returns the full catalog (documented 1.111.0, not validated) | always pass a real slot from `get_time_slots` |
| `silpo_get_time_slots` | date-only `start`/`end` (`"2026-09-02"`) answers with a bare `400 Bad Request` (release-1.111.2 normalization) | typed `get_time_slots` raises `ValueError` before the request; always pass a full timestamp |
| `silpo_update_shopping_cart` | a hand-built `address` without `addressType` (or a shipment without `companyId`/`branchId`) is rejected with `-32602` (release-1.111.3) | copy both from the cart response — `cart.update_payloads`; the typed method also raises `ValueError` naming the offending argument |
| `silpo_get_my_favorites` | `Cannot read properties of null (reading 'id')` — a corrupted favorites entry on the server side. The typed `get_favorites()` raises `SilpoToolExecutionError`; it is **not** a client/model drift. | smoke treats it as skipped; until Silpo fixes it, wrap `get_favorites()` in `try/except SilpoToolExecutionError` or use `call_tool("silpo_get_my_favorites", ...)` and handle the failure |
| `silpo_get_product_details` | `slug: null` chain failure | resolved once `get_products` returns real slugs |

Previously reported quirks that no longer reproduce (re-verified live, Sep 2026):
`silpo_get_category` no longer triggers the fastmcp `id` rejection (it validates
cleanly), `silpo_get_time_slots` accepts `deliveryTypes: ["B2B"]` again
(release-1.111.2 put it back in the enum — it returns an empty slot list), and
`silpo_get_my_certificates` — although still intermittently returning
HTTP 500 — now responds with a normal `certificates` envelope (unwrapped by the
client) that validates cleanly when it does respond.

### Configuration

Configuration is read from environment variables (prefix `SILPO_`) or a `.env`
file. Key settings:

| Variable | Default | Description |
|---|---|---|
| `SILPO_MCP_URL` | `https://mcp.silpo.ua/mcp` | Server endpoint |
| `SILPO_OAUTH_STORAGE_DIR` | `~/.silpo_py_mcp` | Encrypted token store location |
| `SILPO_OAUTH_ENCRYPTION_KEY` | auto-generated | Fernet key (base64) |
| `SILPO_OAUTH_CLIENT_NAME` | `silpo-py-mcp` | Client name for OAuth registration |
| `SILPO_OAUTH_TOKEN_ENDPOINT_AUTH_METHOD` | `none` | DCR auth method: `none` (public client + PKCE, default), `client_secret_post`, `client_secret_basic` |
| `SILPO_OAUTH_CALLBACK_TIMEOUT` | `300.0` | Seconds to wait for the browser callback |
| `SILPO_DEFAULT_REQUEST_TIMEOUT` | `30.0` | Per-request timeout |
| `SILPO_MAX_RATE_LIMIT_RETRIES` | `3` | Retries on HTTP 429 |

Programmatic overrides are supported via `SilpoSettings(...)` or
`SilpoClient.from_fastmcp(client, mcp_url=...)`.

## Schema-driven by design

The exact tool schemas (arguments, JSON Schema) are only known from
`tools/list` after authentication, per the [official docs](https://ai-factory.silpo.ua/docs/mcp).
`SilpoClient` therefore exposes:

- **`list_tools()`** — the live schemas from the server.
- **`call_tool(name, arguments)`** — pass-through calls with typed error mapping.
- **Typed convenience methods** — wrappers over the live tool schemas
  (`get_products`, `get_cart_by_id`, `add_or_update_cart_products`, ...).

If Silpo renames or reshapes tools, only the affected convenience method needs
updating; `call_tool` keeps working.

## Working with the cart

Since release-1.111.3 the update tool wants the cart's own `address` and
`shipments` copied back verbatim, so read them off `cart.update_payloads`
rather than rebuilding them. The cart also separates *what the guest may pay
with* from *what they will pay*:

```python
cart = await client.get_cart_by_id(cart_id)

# what the guest can actually pay with (not cart.payment_type, which is
# "Unknown" until a method is chosen at checkout)
print(cart.available_payment_types)  # ['Cashdesk', 'Card', 'Masterpass', ...]
print(cart.payment.unavailable_types)  # ['BNPL'] — below loan_config.min_total

# the amount to show the guest: total is *before* discounts
print(cart.total_to_pay, cart.totals.total_price)

# why the delivery was cheaper than its list price (the cause is not reported)
print(cart.delivery.sub_total, cart.delivery.sub_discount, cart.delivery.total)

# hand the address/shipments/timeslot straight back to an update
payloads = cart.update_payloads
assert payloads.is_sendable, payloads.missing_fields
await client.update_shopping_cart(
    cart_id,
    cart.delivery_type,
    payloads.timeslot,
    payloads.address,
    payloads.shipments,
)
```

## Error handling

`silpo_py_mcp.exceptions` maps Silpo's documented error responses:

| Server response | Raised |
|---|---|
| `401 invalid_token` | `SilpoAuthError` |
| `403` | `SilpoForbiddenError` |
| `429` (rate limit) | `SilpoRateLimitError` |
| `-32601` method not found | `SilpoToolNotFoundError` |
| Other tool failures | `SilpoToolExecutionError` |
| Schema mismatch / bad response | `SilpoValidationError` |
| Connection / protocol failures | `SilpoConnectionError` |

## Development

```bash
uv sync                  # install deps
uv run pytest            # run tests (all against the in-memory mock)
uv run ruff format .     # format
uv run ruff check .      # lint
uv run pyrefly check     # type check (strict)
uv run pre-commit install  # install git hooks (format/lint/type/tests)
```

### Project layout

```
src/silpo_py_mcp/
├── client.py          # SilpoClient — typed methods + error mapping
├── mock_server.py     # SilpoMockServer — in-memory FastMCP server (40 tools)
├── auth.py            # OAuth 2.1 + PKCE helper, encrypted token storage
├── config.py          # pydantic-settings configuration
├── exceptions.py      # typed exceptions
└── models/            # Pydantic models (product, cart, branch, category, order)
```

## License

MIT