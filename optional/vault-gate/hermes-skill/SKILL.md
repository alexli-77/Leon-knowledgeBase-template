# Vault Gate Hermes Skill

Use this skill when a user asks Hermes to write, capture, read, or revise notes in the private vault.

## Rule

Never write directly to the vault. Always call Vault Gate.

## Routed write

For new notes that have a clear destination, prefer routed writes:

```bash
curl -s "$VAULT_GATE_URL/write" \
  -H "Authorization: Bearer $VAULT_GATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"hermes","route":"daily","title":"TITLE","body":"BODY"}'
```

Use only known routes. If the route is unclear, ask for the route or use `/capture`.

## Capture

For new raw notes, send:

```bash
curl -s "$VAULT_GATE_URL/capture" \
  -H "Authorization: Bearer $VAULT_GATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"hermes","title":"TITLE","body":"BODY"}'
```

## Edit request

For changes to existing notes, rewrites, moves, deletes, or reorganizations, send:

```bash
curl -s "$VAULT_GATE_URL/edit-request" \
  -H "Authorization: Bearer $VAULT_GATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"hermes","title":"REQUEST","body":"FULL REQUEST"}'
```

## Response style

Report the gate result back to the user:

- captured: include target path and run id
- pending-review: explain that the request was queued because it touches existing knowledge
- error: include only the safe error message, never include tokens
