# Authentication flow

This POC implements an **OAuth2-style authorization code** flow with a **mock authorization server** embedded in `mcp-server`. Tokens and sessions persist in **MongoDB**.

## Sequence — unauthenticated private tool

```mermaid
sequenceDiagram
  participant U as User
  participant G as ChatGPT
  participant M as MCP server
  U->>G: Ask about order ORD-1001
  G->>M: tools/call get_order_status (no Bearer)
  M-->>G: { requires_auth: true, auth_url: ".../auth/login" }
  G-->>U: Show login / open auth_url
```

## Sequence — authenticate and retry

```mermaid
sequenceDiagram
  participant U as User
  participant B as Browser
  participant M as MCP server
  participant DB as MongoDB
  participant G as ChatGPT
  U->>B: Open PUBLIC_BASE_URL/auth/login
  B->>M: POST /auth/authorize (demo user)
  M->>DB: Store authorization code (TTL)
  M-->>B: Redirect to /auth/callback?code=...
  B->>M: GET /auth/callback?code=...
  M->>DB: Consume code, create session + access_token
  M-->>U: HTML page with bearer token (JSON via ?format=json)
  U->>G: Paste token into connector settings
  G->>M: tools/call with Authorization Bearer
  M->>DB: Validate token
  M-->>G: Order / member tool success payload
```

## Token and session storage

| Store | Collection | Contents |
|-------|------------|----------|
| MongoDB | `oauth_codes` | Short-lived authorization `code`, `user_id`, `redirect_uri`, `client_id`, `expires_at` (TTL index) |
| MongoDB | `sessions` | `session_id` (cookie), `access_token` (Bearer), `user_id`, `expires_at` (TTL index) |

## HTTP endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/login` | Mock login form |
| POST | `/auth/authorize` | Issues code + redirects |
| GET | `/auth/callback` | Exchanges code for session; optional `?format=json` |
| POST | `/auth/token` | OAuth2 token endpoint (`grant_type=authorization_code`) |
| GET | `/auth/status` | JSON auth status |
| POST | `/auth/logout` | Revoke session |

## ChatGPT session caching

After login, the user (or connector configuration) should **cache the bearer token** for subsequent MCP requests. The MCP server remains stateless regarding ChatGPT; **MongoDB** holds authoritative session rows keyed by `access_token`.
