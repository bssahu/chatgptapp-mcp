# Local setup

## Prerequisites

- **Docker** and **Docker Compose**
- **ngrok** (or another HTTPS tunnel) for remote ChatGPT access
- Optional: **AWS account** with **Bedrock** enabled and **Anthropic Claude Sonnet** access in your chosen region

## 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

- `PUBLIC_BASE_URL` — after ngrok, set to `https://xxxx.ngrok-free.app` (no trailing slash issues; server strips as needed).
- **Bedrock (optional):** `AWS_REGION`, `BEDROCK_MODEL_ID`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` if using temporary credentials.

If Bedrock variables are omitted, `ask_*` tools still return **retrieval-grounded** answers with a clear warning.

## 2. Start Docker Compose

```bash
docker compose up --build -d
docker compose ps
curl -s http://localhost:8000/health
```

Services:

| Service | Host port | Purpose |
|---------|-------------|---------|
| `mcp-server` | 8000 | FastAPI + MCP + OAuth |
| `qdrant` | 6333 | Vector DB API |
| `mongodb` | 27017 | Sessions + OAuth codes |

## 3. Ingest Qdrant collections

```bash
docker compose exec mcp-server python -m app.vector.ingest_public_docs
docker compose exec mcp-server python -m app.vector.ingest_private_docs
```

First run downloads the **fastembed** MiniLM weights into the container (may take a minute).

## 4. Verify MongoDB

```bash
docker compose exec mongodb mongosh shopping_mcp --eval 'db.getCollectionNames()'
```

After a login flow, expect `sessions` and `oauth_codes` collections to appear.

## 5. ngrok

```bash
ngrok http 8000
```

Copy the **HTTPS** forwarding URL into `.env`:

```bash
PUBLIC_BASE_URL=https://YOUR-SUBDOMAIN.ngrok-free.app
```

Restart and **recreate** `mcp-server` after changing `.env` so the process picks up `PUBLIC_BASE_URL`:

```bash
docker compose up -d --force-recreate mcp-server
```

Confirm inside the container (should show your ngrok URL, not `localhost`):

```bash
docker compose exec mcp-server printenv PUBLIC_BASE_URL
```

**Note:** This is **not** a Docker *build* issue—`PUBLIC_BASE_URL` is read at **runtime** from `env_file: .env`, not during `docker compose build`. Rebuilding the image does not reload `.env`.

Private tools embed `PUBLIC_BASE_URL` in `auth_url` responses.

### ngrok warning page vs MCP / APIs

On the **free** tier, ngrok may return an HTML interstitial instead of forwarding to your server. **Programmatic clients** (MCP, curl, scripts) should send:

```http
ngrok-skip-browser-warning: 1
```

(any value works), **or** use a **custom `User-Agent`** that is not a normal browser string.

Add this wherever you configure the HTTP client for **`…/mcp`** (and OAuth/token calls if they fail the same way). The MCP server never receives the request until ngrok forwards it, so this cannot be fixed in Python alone.

If your ChatGPT / MCP UI does not allow extra headers, use **ngrok paid**, **Cloudflare Tunnel**, or another tunnel without this interstitial.

## 6. AWS Bedrock environment variables

Example (adjust model ID to one enabled in your account):

```bash
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Restart `mcp-server` after changes.

## Troubleshooting

- **ngrok returns HTML / MCP fails:** Send `ngrok-skip-browser-warning` on MCP requests (see above), or upgrade ngrok / change tunnel provider.
- **Qdrant empty results:** Re-run ingestion scripts.
- **Mongo connection errors:** Ensure `mongodb` service is healthy before `mcp-server` starts (`depends_on` helps; retry `docker compose up`).
- **Bedrock errors:** Confirm model access in the chosen region and IAM permissions for `bedrock:InvokeModel`.
