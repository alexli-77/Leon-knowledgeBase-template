# Capture API

Minimal HTTP wrapper around `curator/vault_gate.py`.

Endpoints:

- `GET /health`
- `POST /capture`
- `POST /edit-request`

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

