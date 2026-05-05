# Business case

## Why this POC matters

Retailers increasingly deploy **AI assistants** that blend **public merchandising content** with **account-specific data** (orders, loyalty, contracts). Serving both from one agent without leaking private data requires **clear boundaries**, **retrieval layers**, and **standards-based authorization**.

## Enterprise relevance

- **Separation of concerns:** Public catalog + policies vs authenticated CRM / OMS signals mirror how enterprises split CMS and transactional systems.
- **Auditability:** OAuth2 tokens map tool access to identities; MongoDB-backed sessions support revocation and TTL alignment with security policy.
- **Gradual rollout:** Optional Bedrock LLM allows teams to validate retrieval and auth before enabling full generative answers in production.

## MCP value proposition

**Model Context Protocol** gives ChatGPT (and other hosts) a **stable, typed tool surface** instead of ad-hoc REST wrappers per integration. Retail engineering teams can ship **one MCP server** per domain (commerce, support, stores) and reuse hosts across internal and customer-facing pilots.

## Public vs private knowledge access

| Tier | Examples | Discovery |
|------|-----------|-----------|
| Public | SKU descriptions, sizing, policies | JSON catalog + `public_catalog_docs` |
| Private | Member pricing, loyalty rules, order FAQs | `private_member_docs` + authenticated APIs |

Vector indices remain **physically separated** (collections) so ingestion pipelines do not accidentally blend visibility classes.

## OAuth-secured agentic commerce assistant

Tool-level auth responses (`requires_auth`, `auth_url`) let the **model** cooperate with the **host UI**: users authenticate when needed, then **retry** the same intent with an elevated session—mirroring how human agents escalate to verified channels.

## Future roadmap

1. Replace mock OAuth with **corporate IdP** (OIDC) and PAR/PKCE hardening.
2. Add **per-tool scopes** and policy-as-code for regulated categories (payments, health-adjacent claims).
3. Introduce **human-in-the-loop** approvals for high-risk cart mutations.
4. Move embeddings to **managed Bedrock Titan** or enterprise-approved models with audit trails.
5. Ship **observability**: trace IDs across ChatGPT → MCP → downstream APIs.
