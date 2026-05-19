# Capture API

Minimal HTTP wrapper around `curator/vault_gate.py`.

Endpoints:

- `GET /health`
- `POST /capture`
- `POST /edit-request`
- `POST /write`

Every write endpoint requires:

```text
Authorization: Bearer <VAULT_GATE_TOKEN>
```

Payload:

```json
{
  "source": "discord",
  "title": "Short title",
  "body": "Markdown body"
}
```

`/write` also requires a route:

```json
{
  "source": "discord",
  "route": "daily",
  "title": "Today",
  "body": "Markdown body"
}
```

Routes are server-side allowlisted through `VAULT_GATE_ROUTES_JSON`.
