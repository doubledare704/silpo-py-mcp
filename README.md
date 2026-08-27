# silpo-py-mcp

Typed Python client for the official **Silpo** MCP server
([`https://mcp.silpo.ua/mcp`](https://ai-factory.silpo.ua/docs/mcp)).

Built on [FastMCP `3.4.7`](https://gofastmcp.com/) for the *Silpo AI Factory*
hackathon. One library, two modes:

- **Real server** — Streamable HTTP transport with OAuth 2.1 + PKCE, encrypted
  on-disk token storage, 39 typed methods mirroring the documented
  `silpo_*` tools.
- **In-memory mock** — a FastMCP server that implements the same 39 tools with
  realistic fixtures, so you can develop and test without a Silpo account.

Requires **Python 3.12+**.

---

## Install

```bash
uv add silpo-py-mcp            # in your project
# or, for local development of this package:
uv sync
```

## Quick start (mock — no auth needed)

```python
import asyncio
from silpo_py_mcp import SilpoClient


async def main() -> None:
    async with SilpoClient.for_mock() as client:
        result = await client.get_products(query="сир")
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

> **Note on typed methods vs the real server.** The real `tools/list` schemas
> (which `call_tool` follows verbatim) differ from the documented ones the
> mock is built on — e.g. `silpo_get_products` takes `branchId`/`deliveryType`/
> `timeslotStart`/`timeslotEnd`, `silpo_find_address` takes `address`,
> `silpo_get_category` takes `categorySlug`, and cart tools take
> `shoppingCartId`. The typed convenience methods still target the documented
> names; use `call_tool` for live calls until they are reconciled. Responses
> come back JSON-like (nested FastMCP `Root` dataclasses are unwrapped
> automatically).

### Smoke test against the real server

`examples/real_smoke.py` verifies the live contract and runs a read-only
battery of calls:

```bash
uv run examples/real_smoke.py
```

On the first run a browser opens for login at `auth.silpo.ua`; afterwards the
encrypted token in `~/.silpo_py_mcp` is reused. The script checks:

- live `tools/list` matches the 39 documented tools and prints every live
  signature (arg names/types),
- a read-only battery of `call_tool` calls built from the live schemas
  (branches, address, delivery types, time slots, categories tree, promotions,
  products, profile, favorites, loyalty, coupons, orders, promos, certificates).

Failures are reported per check without aborting — server-side schema bugs and
drift between the real server and the mock show up as `✗` lines. Exits
non-zero if the tool-name contract is violated or a battery call fails.

### Known server-side failures (verified live, Aug 2026)

| Tool | Symptom | Root cause |
|---|---|---|
| `silpo_get_category` | fastmcp rejects the response: `Additional properties are not allowed ('id' was unexpected)` | the server declares an output schema with only `slug`/`title`, but returns `id` as well |
| `silpo_get_products` | `Error in get-products: API returned 400 Bad Request` | backend rejects a request built from its own live schema |
| `silpo_get_time_slots` | `-32602 Invalid arguments` for `deliveryTypes: ["B2B"]` | `silpo_get_available_delivery_types` returns `B2B`, but `silpo_get_time_slots`' enum does not accept it |
| `silpo_get_my_certificates` | `Error in get-my-certificates: API returned 500 Internal Server Error` | server-side HTTP 500 |
| `silpo_get_product_details` | fails with `slug: null` in the smoke battery | chain failure — no product slug was obtained because `silpo_get_products` returned 400 |

opencode -s ses_fdff84746ffeyxZ0WSuLDho32B

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
- **Typed convenience methods** — stable wrappers over documented tool names
  (`get_products`, `get_cart_by_id`, `add_or_update_cart_products`, ...).

If Silpo renames or reshapes tools, only the affected convenience method needs
updating; `call_tool` keeps working.

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
uv run pytest            # run tests (32 tests, all against the in-memory mock)
uv run ruff format .     # format
uv run ruff check .      # lint
uv run pyrefly check     # type check (strict)
uv run pre-commit install  # install git hooks (format/lint/type/tests)
```

### Project layout

```
src/silpo_py_mcp/
├── client.py          # SilpoClient — typed methods + error mapping
├── mock_server.py     # SilpoMockServer — in-memory FastMCP server (39 tools)
├── auth.py            # OAuth 2.1 + PKCE helper, encrypted token storage
├── config.py          # pydantic-settings configuration
├── exceptions.py      # typed exceptions
└── models/            # Pydantic models (product, cart, branch, category, order)
```

## License

MIT