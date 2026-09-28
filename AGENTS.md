# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project

`silpo-py-mcp` — a typed Python client for the official Silpo MCP server
(`https://mcp.silpo.ua/mcp`). Built on FastMCP `3.4.7` for the Silpo AI
Factory hackathon. Python 3.12+.

Two connection modes with the **same client interface**:

- **Real server**: Streamable HTTP transport + OAuth 2.1/PKCE, encrypted disk
  token storage. First connection opens a browser for login at `auth.silpo.ua`.
- **In-memory mock**: `SilpoMockServer` — a FastMCP server implementing the 40
  documented `silpo_*` tools with realistic fixtures. No network/auth needed.

## Commands

Use `uv` — do not activate venvs manually or use `pip`.

```bash
uv sync                        # install all deps (incl. dev)
uv run pytest                  # run tests (all run against the in-memory mock)
uv run ruff format .           # format
uv run ruff check .            # lint
uv run pyrefly check           # type-check (strict)
uv run pre-commit run --all-files  # full validation loop
uv run examples/quickstart.py  # run the demo (mock)
uv run examples/real_smoke.py  # run against the real server (first run: browser login)
uv run python -m silpo_py_mcp ... # run any module
```

Validation gate (also installed as pre-commit hooks):
`ruff format --check` → `ruff check --fix` → `pyrefly check` → `pytest`.
Always run all four before finishing a change.

## Tool mapping (40 documented tools)

The official docs live at <https://ai-factory.silpo.ua/docs/mcp>. Exact
schemas are only known at runtime via `tools/list` after auth. Tool names,
argument names and response keys use **camelCase** (e.g. `silpo_get_products`
takes `pageSize`, `categoryId`, `onSale`). The mock mirrors these exactly.

| Group | Tools |
|---|---|
| Location/delivery (6) | `silpo_find_address`, `silpo_get_available_delivery_types`, `silpo_list_branches`, `silpo_get_time_slots`, `silpo_find_nova_poshta_settlements`, `silpo_find_nova_poshta_offices` |
| Product search (7) | `silpo_find_products_batch`, `silpo_get_products`, `silpo_get_product_details`, `silpo_get_similar_products`, `silpo_get_replacements`, `silpo_get_my_favorites`, `silpo_add_or_update_favorite_products` |
| Catalog (6) | `silpo_get_promotions`, `silpo_get_popular_categories`, `silpo_get_category`, `silpo_get_categories`, `silpo_get_categories_tree`, `silpo_get_product_sets` |
| Cart (8) | `silpo_get_my_shopping_cart`, `silpo_create_shopping_cart`, `silpo_get_shopping_cart_by_id`, `silpo_add_or_update_cart_products`, `silpo_remove_cart_products`, `silpo_clear_shopping_cart`, `silpo_update_shopping_cart`, `silpo_add_or_update_certificates` |
| Orders (2) | `silpo_get_my_online_orders`, `silpo_get_my_offline_orders` |
| Profile (4) | `silpo_get_my_profile`, `silpo_get_my_delivery_addresses`, `silpo_get_my_family`, `silpo_get_my_food_restrictions` |
| Loyalty (7) | `silpo_get_loyalty_info`, `silpo_get_my_coupons`, `silpo_get_coupon_details`, `silpo_get_my_promos`, `silpo_get_promo_codes`, `silpo_get_my_certificates`, `silpo_get_my_premium_subscription` |

### Documented error responses

| Server | Raised exception |
|---|---|
| `401 invalid_token` | `SilpoAuthError` (refresh or re-auth) |
| `403` | `SilpoForbiddenError` |
| `429` (per-user rate limit, `Cookie: mcp-user`) | `SilpoRateLimitError` |
| `-32601` method not found | `SilpoToolNotFoundError` |
| other tool failures | `SilpoToolExecutionError` |

## Architecture

```
src/silpo_py_mcp/
├── client.py        # SilpoClient: typed methods + call_tool passthrough + error mapping
├── mock_server.py   # SilpoMockServer: in-memory FastMCP server (40 tools, camelCase args)
├── auth.py          # build_encrypted_token_storage + build_oauth (PKCE, DCR, auto-refresh)
├── config.py        # SilpoSettings (env prefix SILPO_)
├── exceptions.py    # typed exception hierarchy
├── tools.py         # SilpoTool StrEnum (40 silpo_* names, single source)
└── models/          # Pydantic models; camelCase aliases + populate_by_name
```

Key design decisions:

1. **Schema-driven core.** `SilpoClient.call_tool(name, arguments)` passes args
   through verbatim and maps errors. Typed methods (`get_products`, ...) are a
   stable convenience layer — they may break if Silpo changes schemas, but the
   raw path never does.
2. **One interface, two transports.** `SilpoClient.for_mock()` (in-memory) and
   `SilpoClient.for_real_server()` (Streamable HTTP + OAuth). Tests always run
   against the mock so the suite needs no network or Silpo credentials.
3. **Mock arg names must match the real API.** If you add a mock tool or change
   arguments, keep them camelCase and consistent with the live `tools/list`
   schemas (dump them with `examples/real_smoke.py`), and update `SilpoTool`
   in `src/silpo_py_mcp/tools.py` (single source; `EXPECTED_TOOLS` derives from it).
4. **Token security.** OAuth tokens are stored encrypted at rest (Fernet) under
   `~/.silpo_py_mcp` by default. Never log tokens; keep them server-side.

## Conventions

- Python 3.12+, `from __future__ import annotations`, type annotations everywhere.
- Formatting/lint via Ruff (line length 100), typing via pyrefly `strict`.
- Pydantic models: snake_case field names with camelCase aliases matching the
  Silpo API; `populate_by_name=True` is set on the shared `SilpoModel` base.
- Tests live in `tests/` and use `pytest` with `asyncio_mode = "auto"`.
- No comments unless they clarify non-obvious intent (project follows the
  "no unnecessary comments" convention).
- Keep README.md and this file in sync with reality when the API changes.

## Working notes

- FastMCP is pinned to `==3.4.7` deliberately (stable). When upgrading,
  check the client transport/OAuth APIs on <https://gofastmcp.com/> first.
- `key-value`'s `DiskStore` needs `diskcache` and `pathvalidate` (extras are
  installed explicitly in `pyproject.toml`).
- The mock cart is scoped per-session via `Context.session_id`, so parallel
  clients do not share carts.
- **OAuth DCR must request `token_endpoint_auth_method: "none"`** (public
  client + PKCE). Silpo's AS otherwise registers a confidential client
  (`client_secret_basic`) and the `mcp` library then sends both a Basic header
  and `client_id` in the body, which the server rejects with "Client must not
  use multiple authentication methods".
- **All 40 tools are reconciled to the live `tools/list` schemas** (verified
  live, Sep 2026; re-verified Sep 7 2026; reconciled with server
  release-1.110.0 on Sep 10 2026 — no drift in tool names, arg names or
  required sets; reconciled with server release-1.110.1 on Sep 11 2026;
  re-verified Sep 14 2026 — still 40 tools, no renames, no required-set
  changes; reconciled with server release-1.111.0/1.111.1 on Sep 25 2026 —
  still 40 tools, no renames; reconciled with server release-1.111.2 on
  Sep 28 2026 — still 40 tools, no renames, no required-set changes; plus
  the release-1.110.0 `silpo_get_product_details` output fix
  below).
  The mock exposes exactly the live argument names and the
  typed methods send exactly the live payloads. Context args
  (`branchId`/`deliveryType`/`timeslotStart`/`timeslotEnd`) are required where
  the live schema requires them — since 1.110.1 this includes
  `silpo_get_similar_products` (breaking: `deliveryType`/`timeslotStart`/
  `timeslotEnd` are now required for accurate stock); cart tools take `shoppingCartId`;
  `silpo_add_or_update_cart_products` takes `products`
  (`[{productId, companyId, branchId, quantity, addQuantity?, comment?}]` —
  omitted/false `addQuantity` replaces the quantity, `true` adds to it);
  `silpo_find_products_batch` takes `products` as a list of strings;
  `silpo_add_or_update_favorite_products` takes `actions`
  (`[{productId, externalProductId, toDelete}]`);
  `silpo_add_or_update_certificates` takes `certificatesToAdd`/
  `certificatesToRemove` as `[{barcode, pincode?}]` objects (plain barcode
  strings are converted client-side). `DeliveryType` covers all 16 live enum
  values. Use `examples/real_smoke.py`
  to re-dump the live schemas after server updates.
- **Response shapes are reconciled too** (verified live, Sep 10 2026, against
  real data for every group; product shapes re-verified Sep 11 2026 for
  release-1.110.1). Every live
  response is wrapped in `{success, summary, <data>, meta?}`; the typed
  methods unwrap it via `_unwrap_payload` (lists and dicts alike).
  Coupon eligibility comes from `canBeAppliedToOrder` on
  `silpo_get_coupon_details` (requires both `active` and `state="Активний"`);
  the live cart nests products under `shipments[].products`, sums under
  `calculation` (incl. `validations`), and loyalty/checkout links at the top
  level — `get_cart_by_id` maps those onto `SilpoCart`. Models accept both
  the live field names (`id`/`name`/`start`/`end`/`deliveryType`/`available`)
  and the documented/mock ones via `AliasChoices`, so the mock's fixtures
  keep validating. `find_products_batch` (`queries` → `results`) and
  `get_products` (`products` + `meta.total`) are normalized client-side.
  Product results carry `displayPrice` (`fromPrice`/`toPrice` filter by it);
  `get_product_details` carries `displayPrice`/`image`/`specialPrices`/
  `externalProductId`; batch `meta.droppedCount` surfaces as
  `BatchProductResult.dropped_count`.
- **Release-1.111.0/1.111.1 fixes (client 0.6.0).** `silpo_get_products`
  requires one of `category`/`mustHavePromotion`/`promotionCode`/`set`
  (clear message since 1.111.0, was a raw 400 — `get_products` raises
  `ValueError` client-side and the mock enforces it; `inStock`/`limit`/sort
  alone do not satisfy it) and never validates
  `timeslotStart`/`timeslotEnd` (bogus slot silently returns the full
  catalog — always pass a real `get_time_slots` slot).
  `silpo_get_time_slots` accepts singular `deliveryType` as an alias for
  `deliveryTypes` (mock accepts both; typed method sends the full plural
  list), strips millisecond timestamps upstream (client strips them too via
  `_strip_millis`), returns no duplicates, and carries `serviceFee`
  (`TimeSlot.service_fee`; SelfPickup "Сервісний збір"). `silpo_find_address`
  flags unmatched house numbers via `warning`/`houseNumberMatched`
  (`Address.warning`/`house_number_matched`; mock flags queries missing the
  fixture house number). `silpo_get_available_delivery_types` coordinates are
  only validated for home-delivery types. `silpo_get_shopping_cart_by_id`
  carries `serviceFee` (`SilpoCart.service_fee`/`CartTotals.service_fee`,
  mapped from top level or `calculation`; mock: 15.0 for SelfPickup, else
  0.0). `examples/real_smoke.py` probes each fix live.
- **Release-1.111.2 fixes (client 0.7.0).** `silpo_get_time_slots` normalizes
  its timeslot bounds: `Z`, `+00:00` and naive (offset-less) stamps are all
  accepted and read as UTC, millisecond fractions are stripped, and a date-only
  or unparseable bound answers a bare `400 Bad Request` — the client rejects it
  first with `ValueError` (`_normalize_slot_bound`). Its `deliveryTypes`/
  `deliveryType` enum is now the narrower 9-value `TimeSlotDeliveryType`
  (`SelfPickup`, `DeliveryHome`, `DeliveryExpress`, `LongDelivery`,
  `NovaPoshta`, `DeliveryExpressByPromise`, `WideAssortDelivery`, `B2B`,
  `PreOrder`) — a strict subset of `DeliveryType`, which keeps all 16 values
  used by the other tools; `Unknown`/`JustIn`/`JustInPost` now fail with
  `-32602` while `B2B` is accepted again (the old 0.6.0 `B2B` quirk is gone).
  `limit` is bounded to 1..100. `get_time_slots` validates all three
  client-side; the mock enforces the same rules and now actually filters slots
  by the requested window. `silpo_create_shopping_cart` requires `addressType`
  (`house`/`flat`/`office`/`point`/`self-pickup`/`nova-poshta`) — the smoke
  fills it and probes that write tool once (a second call is rate-limited).
- **Release-1.110.0 `silpo_get_product_details` fix.** The server no longer
  returns stale catalog-wide `displayPrice`/`price` — pricing and
  availability are the requested branch's real offer, with an explicit
  `hasOfferAtBranch` flag (`False` = no real offer at that branch).
  `ProductDetail`/`SilpoProduct` expose it as `has_offer_at_branch`; the mock
  echoes the requested `branchId` and returns `stock=0`/`available=False`
  when the flag is `False`. `get_product_details` docstring tells callers to
  check the flag first. `examples/real_smoke.py` logs the live flag.
- Real tool responses come back as FastMCP `Root` dataclasses; `_extract_payload`
  unwraps them via `dataclasses.asdict` so `call_tool` returns plain JSON.
- Server quirks observed live: `silpo_get_my_certificates` sometimes returns
  HTTP 500; `silpo_get_my_favorites` fails server-side with
  `Cannot read properties of null (reading 'id')` for a corrupted favorites
  entry (pre-existing, unrelated to the client).