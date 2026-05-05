# ChatGPT App packaging (POC)

This folder holds **connector-oriented metadata** for wiring ChatGPT (or another MCP host) to the shopping MCP server exposed via **ngrok**.

## MCP endpoint

Once `PUBLIC_BASE_URL` matches your tunnel:

```text
https://<your-ngrok-host>/mcp
```

Use **Streamable HTTP** MCP transport at that path (FastMCP default under FastAPI mount).

### “Does not implement OAuth” (ChatGPT / Cursor MCP UI)

If **Authentication** is set to **OAuth**, the host tries to **discover** OAuth metadata (for example `/.well-known/oauth-protected-resource` and related MCP OAuth endpoints). **This POC does not register FastMCP’s OAuth provider**, so discovery fails even though mock login exists at `/auth/login`.

**What to do here**

1. Set **Authentication** to **None** / **No auth** (not OAuth).
2. Use MCP URL **`https://<ngrok-host>/mcp`** (include the **`/mcp`** path unless your UI says it adds it automatically).
3. For **private tools**, open `/auth/login` in a browser, copy the **bearer token**, then paste it wherever the connector stores headers / secrets (often “Custom headers” or “Access token”), or pass `access_token` on tool calls if supported.

Full MCP-standard OAuth discovery would require wiring FastMCP / MCP SDK **OAuth authorization server** integration—not just the mock routes in this repo.

### ngrok free tier interstitial

If MCP connects to `*.ngrok-free.app` and gets HTML errors or handshake failures, configure the connector’s HTTP client to send:

```http
ngrok-skip-browser-warning: 1
```

(or any non-browser **`User-Agent`**). That header must be set **outbound from ChatGPT / the MCP client**; ngrok strips the warning only when it sees this signal. Paid ngrok accounts skip this page without extra headers.

### OpenAI “New App” / connector create fails (generic error) + ngrok free

**Yes, this can be the ngrok free interstitial.** When you click **Create**, OpenAI’s servers call your **MCP URL** to validate it. They run that check **from their infrastructure**—you **cannot** configure OpenAI to add `ngrok-skip-browser-warning` or a custom `User-Agent`. If ngrok returns the **HTML warning page** instead of the MCP transport, validation fails and you get a generic “something went wrong” error (not a clear ngrok message).

**What you can do**

| Approach | Notes |
|----------|--------|
| **ngrok paid** | Often removes the interstitial for automated access (see [ngrok docs](https://ngrok.com/docs) for your plan). |
| **Another tunnel** | e.g. **Cloudflare Tunnel**, **Tailscale Funnel**, a small **VPS + HTTPS**—no `ngrok-skip-browser-warning` game. |
| **Public deploy** | Run the same Docker stack on a host with a real URL (Fly.io, EC2, etc.). |
| **Confirm URL** | Use the full Streamable HTTP path, e.g. `https://YOUR-NGROK-HOST.ngrok-free.app/mcp`. |

There is **no** setting in this repo or in the OpenAI UI to “inject” the ngrok bypass header for **their** health check—workarounds are tunnel/plan or hosting, not a header you configure for OpenAI.

## OAuth for private tools

1. Open `https://<your-ngrok-host>/auth/login`, complete mock login, copy **access token**.
2. Configure your MCP connector to send:

```http
Authorization: Bearer <access_token>
```

Many hosts store this as a **session-scoped secret** after first login; consult your ChatGPT App / connector docs for where to paste OAuth tokens.

If the host cannot attach headers, private tools accept an optional `access_token` argument as an escape hatch.

## Files

| File | Purpose |
|------|---------|
| `app_manifest/openapi.yaml` | REST-oriented sketch of OAuth + health endpoints (for Actions-style integrations or documentation). |
| `app_manifest/chatgpt-gpt-schema.json` | Minimal JSON schema snippet describing tool intents for internal docs (not an official OpenAI submission format). |

## Private tool handshake

When unauthenticated, tools return:

```json
{
  "requires_auth": true,
  "auth_url": "https://<your-ngrok-host>/auth/login",
  "message": "Please authenticate to access order status or member-only catalog."
}

```

Surface `auth_url` as a **login button** or link in the ChatGPT UI, then retry after the user completes OAuth.
