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
   arguments, keep them camelCase and consistent with the docs, and update
   `SilpoTool` in `src/silpo_py_mcp/tools.py` (single source; `EXPECTED_TOOLS` derives from it).
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
- **The real `tools/list` schemas differ from the docs the mock is built on.**
  Verified live (Aug 2026): `silpo_get_products` takes
  `branchId`/`deliveryType`/`timeslotStart`/`timeslotEnd` (+ filters),
  `silpo_find_address` takes `address`, `silpo_get_available_delivery_types`
  takes `latitude`/`longitude`, `silpo_get_category` takes `categorySlug`,
  cart tools take `shoppingCartId`. Typed methods still target the documented
  names — use `call_tool` (or `examples/real_smoke.py`) for live calls until
  the mock and typed methods are reconciled.
- Real tool responses come back as FastMCP `Root` dataclasses; `_extract_payload`
  unwraps them via `dataclasses.asdict` so `call_tool` returns plain JSON.
- Server quirks observed live: `silpo_get_category` declares an output schema
  that forbids the `id` field it actually returns (fastmcp rejects it);
  `silpo_get_my_certificates` sometimes returns HTTP 500.