# ChatGPT App + Shopping MCP (Proof of Concept)

Monorepo for a **shopping-site AI assistant** where ChatGPT connects to a **FastMCP** server over HTTP (typically via **ngrok**). Public catalog and documentation are available without login; **orders** and **member-only** content require **mock OAuth2**, with sessions stored in **MongoDB** and embeddings in **Qdrant**. Optional **AWS Bedrock** powers Claude Sonnet answers.

## Repository layout

| Path | Purpose |
|------|---------|
| `mcp-server/` | FastAPI + FastMCP, OAuth routes, tools, sample data, ingestion |
| `chatgpt-app/` | Manifest-style notes, OpenAPI sketch, connector hints |
| `docs/` | Architecture, auth, business case, setup, testing |
| `docker-compose.yml` | **mcp-server**, **qdrant**, **mongodb** |

## Quick start (exact commands)

```bash
cd /path/to/chatgptapp-mcp
cp .env.example .env
# Optional: set PUBLIC_BASE_URL after ngrok, and AWS Bedrock variables for full LLM answers.

docker compose up --build -d
```

Ingest sample markdown into Qdrant (after containers are healthy):

```bash
docker compose exec mcp-server python -m app.vector.ingest_public_docs
docker compose exec mcp-server python -m app.vector.ingest_private_docs
```

Expose the API publicly (for ChatGPT / remote MCP clients):

```bash
ngrok http 8000
```

Set in `.env`:

```bash
PUBLIC_BASE_URL=https://YOUR-SUBDOMAIN.ngrok-free.app
```

Restart the stack so `PUBLIC_BASE_URL` is picked up:

```bash
docker compose up -d
```

### ngrok free tier: “Visit Site” warning on API traffic

ngrok’s **browser warning** is returned **before** your app sees the request. Automated MCP calls must identify as non-browser traffic:

- Send header **`ngrok-skip-browser-warning`** with any value (for example `true` or `1`), **or**
- Send a **non-standard `User-Agent`** (anything other than typical browser UAs).

Configure that on the **MCP client / ChatGPT connector** that calls `https://…ngrok-free.app/mcp`. Your FastAPI server cannot strip this page for you. Alternatively use a **paid ngrok plan** or another tunnel that does not inject this page.

Example with curl:

```bash
curl -s -H "ngrok-skip-browser-warning: 1" https://YOUR-SUBDOMAIN.ngrok-free.app/health
```

## Endpoints (local)

| URL | Description |
|-----|-------------|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/mcp` | Streamable HTTP MCP (FastMCP) |
| `http://localhost:8000/auth/login` | Mock OAuth2 login UI |
| `http://localhost:8000/auth/callback` | OAuth callback / token display |
| `http://localhost:8000/auth/status` | Session status (JSON) |

## Postman samples

Use a **Postman Environment** (or collection variables) such as:

| Variable | Example | Notes |
|----------|---------|--------|
| `base_url` | `http://localhost:8000` | or `https://YOUR-SUBDOMAIN.ngrok-free.app` |
| `mcp_session_id` | *(empty until step 2)* | Copy from **response** headers: `mcp-session-id` |
| `mcp_protocol_version` | `2024-11-05` | Prefer value from initialize **`result.protocolVersion`** (see SSE note below) |
| `access_token` | *(after OAuth)* | For private tools + `/auth/status` |

### Headers to add on every request (collection-level recommended)

| Header | Value |
|--------|--------|
| `ngrok-skip-browser-warning` | `1` |
| `Accept` | `application/json, text/event-stream` |
| `Content-Type` | `application/json` |

The MCP transport **requires** `Accept` to include **both** JSON and SSE unless the server is configured for JSON-only responses. Omitting this often yields **406 Not Acceptable**.

### 1. Health check

- **GET** `{{base_url}}/health`  
- Headers: table above (no MCP session headers yet).

### 2. MCP — `initialize` (first POST)

- **POST** `{{base_url}}/mcp`  
- Headers: table above only. Do **not** send `mcp-session-id` or `mcp-protocol-version` on this call (omit them entirely).

**Why you might see `Session not found` (-32600) here**

The MCP stack treats **`mcp-session-id` present but unknown** as an error: stale ID, **server/container restart** (in-memory sessions gone), or Postman sending **`mcp-session-id` with an empty value** when the env var is unset—**remove that header** on this request, or turn off header inheritance from the collection for `initialize`.

- Body → raw → JSON:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "postman-test",
      "version": "1.0.0"
    }
  }
}
```

After sending, open the **Headers** tab on the **response** and copy `mcp-session-id` into `{{mcp_session_id}}`. If the body is an **SSE stream**, parse the first JSON event for `result.protocolVersion`, or temporarily use `2024-11-05` for `{{mcp_protocol_version}}`.

### 3. MCP — `notifications/initialized`

- **POST** `{{base_url}}/mcp`  
- Headers: table above **plus**:

| Header | Value |
|--------|--------|
| `mcp-session-id` | `{{mcp_session_id}}` |
| `mcp-protocol-version` | `{{mcp_protocol_version}}` |

- Body:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

### 4. MCP — `tools/list`

- **POST** `{{base_url}}/mcp`  
- Same extra headers as step 3.  
- Body — **`params` must be empty or pagination-only** (`cursor`). Do **not** reuse `initialize` fields here; that mismatch returns **`Invalid request parameters` (-32602)**.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### 5. MCP — `tools/call` (public example)

- **POST** `{{base_url}}/mcp`  
- Same headers as step 3.  
- Body:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_public_catalog",
    "arguments": {
      "query": "running shoes under 150"
    }
  }
}
```

### 6. MCP — `tools/call` (private example — after OAuth)

Complete `/auth/login` in a browser, then set `{{access_token}}` from the callback page.  
- **POST** `{{base_url}}/mcp`  
- Headers: step 3 **plus**:

| Header | Value |
|--------|--------|
| `Authorization` | `Bearer {{access_token}}` |

- Body:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "get_order_status",
    "arguments": {
      "user_id": "user-001",
      "order_id": "ORD-1001"
    }
  }
}
```

### 7. Optional — `GET /auth/status`

- **GET** `{{base_url}}/auth/status`  
- Headers: `ngrok-skip-browser-warning: 1` and, if you have a token, `Authorization: Bearer {{access_token}}`.

### Postman: “I called `tools/call` but the response has `result.tools`”

That shape is **only** returned by **`tools/list`**, not by **`tools/call`**.

| In `result` | Produced by | Typical `tools/call` for `search_public_catalog` |
|-------------|-------------|---------------------------------------------------|
| `tools`: array of tool definitions | **`tools/list`** | — |
| `content`: array of text/resource blocks (often JSON in a text block) | **`tools/call`** | Includes fields like `catalog_matches`, `documentation_matches` inside structured or text content |

So you are almost always **viewing the wrong response** (another request tab, History entry, or cached body), or the **outbound body** is still **`tools/list`** (confirm in **Postman → View → Show Postman Console**). Use **unique `id` values** per request (e.g. don’t reuse `1` after `initialize`).

## Documentation

- [Architecture](docs/architecture.md)
- [Authentication flow](docs/auth_flow.md)
- [Business case](docs/business_case.md)
- [Local setup](docs/local_setup.md)
- [Testing guide](docs/testing_guide.md)
- [ChatGPT App packaging](chatgpt-app/README.md)

## MCP tools

**Public:** `search_public_catalog`, `ask_public_product_question`  
**Private (OAuth):** `get_order_status`, `search_member_catalog`, `ask_private_member_question`

Private tools return `requires_auth` + `auth_url` when no valid bearer token is present.

## Publishing on GitHub

```bash
git init
git add .
git status   # confirm `.env` is not listed (use `.env.example` only in repo)
git commit -m "Initial commit: shopping MCP POC"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

GitHub Actions runs **`docker compose config`** and builds the **`mcp-server`** image on pushes and PRs to `main`/`master` (see [.github/workflows/ci.yml](.github/workflows/ci.yml)). Contributors: see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This repository is licensed under the [MIT License](LICENSE). Proof-of-concept sample code—adapt as needed for your organization.
