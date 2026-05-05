# Testing guide

## Public prompts (no authentication)

Use after `docker compose up` and ingestion.

| Prompt | Expected behavior |
|--------|-------------------|
| "Show me running shoes under $150." | `search_public_catalog` returns Apex Runner Pro ($129.99) plus any doc hits. |
| "What is your return policy?" | `ask_public_product_question` answers using `return_policy.md` chunk + optional Bedrock. |
| "Do you sell wireless headphones?" | Catalog match `Pulse Wireless Headphones`. |
| "Which products are good for travel?" | FAQ / catalog mentions backpack, mug, headphones. |

## Private prompts (authentication required)

Before calling tools, complete OAuth:

1. Open `PUBLIC_BASE_URL/auth/login` (local: `http://localhost:8000/auth/login`).
2. Submit as **user-001** (Alex) or **user-002** (Sam).
3. Copy the **access token** from the callback page (or `GET /auth/callback?code=...&format=json`).
4. Configure your MCP client to send `Authorization: Bearer <token>` **or** pass `access_token` on private tool arguments where supported.

| Prompt | User | Expected |
|--------|------|----------|
| "What is the status of my order ORD-1001?" | user-001 | Order shipped; items listed. |
| "Show me member-only smartwatch deals." | either | `search_member_catalog` returns Vertex Member Smartwatch. |
| "What premium products are available for members?" | either | Member SKUs + private vector snippets. |
| "What loyalty benefits do I have?" | either | `ask_private_member_question` cites loyalty markdown. |

**user-002** order references: `ORD-2001`, `ORD-2002`.

## curl sanity checks

```bash
curl -s http://localhost:8000/health
curl -s "http://localhost:8000/auth/status"
```

After obtaining a token:

```bash
curl -s -H "Authorization: Bearer YOUR_TOKEN" "http://localhost:8000/auth/status"
```

## MCP client testing

Use any Streamable HTTP MCP client pointed at:

```text
http://localhost:8000/mcp
```

(or your ngrok HTTPS URL + `/mcp`).

List tools and invoke:

- `search_public_catalog` with `{"query": "running shoes"}`
- `get_order_status` with `{"user_id": "user-001", "order_id": "ORD-1001"}` **with** Bearer header set.

Without Bearer, `get_order_status` returns:

```json
{
  "requires_auth": true,
  "auth_url": "http://localhost:8000/auth/login",
  "message": "Please authenticate..."
}
```

## ChatGPT prompts (copy/paste)

**Public**

- Show me running shoes under $150.
- What is your return policy?
- Do you sell wireless headphones?
- Which products are good for travel?

**Private (after login / token)**

- What is the status of my order ORD-1001?
- Show me member-only smartwatch deals.
- What premium products are available for members?
- What loyalty benefits do I have?
