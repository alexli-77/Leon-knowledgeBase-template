# Remote macOS client usage

This guide explains how a remote macOS device or local automation service can send requests to a Vault Gate server.

Use placeholders in docs and code examples:

- `SERVER_VAULT_GATE_URL`: base URL of the Vault Gate API, for example `http://TAILSCALE_IP:8787`
- `VAULT_GATE_TOKEN`: bearer token generated on the server

Never commit real IP addresses, API tokens, bot tokens, private vault paths, or private notes.

## Recommended setup

Install the client on the remote macOS device:

```bash
./client-install.sh install \
  --url "SERVER_VAULT_GATE_URL" \
  --token "VAULT_GATE_TOKEN"
```

Rules:

- `--url` is the base URL only, without `/capture` or `/edit-request`
- `--token` is the token itself, without the `Bearer ` prefix
- the installer writes `~/.vault-gate-client/config.env`
- the installer creates `~/.local/bin/vault-capture`
- the installer creates `~/.local/bin/vault-edit-request`

If `~/.local/bin` is not in `PATH`, add this to the shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Command-line usage

Capture a new note:

```bash
vault-capture "Title" "Markdown body"
```

Capture from stdin:

```bash
echo "Markdown body" | vault-capture "Title"
```

Capture clipboard text:

```bash
pbpaste | vault-capture "Clipboard capture"
```

Queue a request to modify existing notes:

```bash
vault-edit-request "Please summarize today's capture inbox"
```

Use `/capture` for new material. Use `/edit-request` for edits, rewrites, moves, deletes, merges, or reorganizations.

## HTTP API

### Read a file

```text
GET SERVER_VAULT_GATE_URL/read?path=RELATIVE_PATH
```

Headers:

```text
Authorization: Bearer VAULT_GATE_TOKEN
```

Response (200):

```json
{
  "status": "ok",
  "path": "10_Daily/2026-05-18.md",
  "content": "# 2026-05-18\n..."
}
```

- `RELATIVE_PATH` must be relative to the vault root (e.g. `10_Daily/2026-05-18.md`, `99_Meta/routing.md`).
- Hidden segments (`.git`, `.obsidian`) and `..` are rejected.
- Returns 404 if the file does not exist.

### Write new content

```text
POST SERVER_VAULT_GATE_URL/capture
```

### Queue an edit

```text
POST SERVER_VAULT_GATE_URL/edit-request
```

Headers:

```text
Authorization: Bearer VAULT_GATE_TOKEN
Content-Type: application/json
```

Body:

```json
{
  "source": "macos",
  "title": "Title",
  "body": "Markdown body"
}
```

Suggested `source` values:

- `macos`
- `raycast`
- `alfred`
- `shortcut`
- `script`
- `service`

## curl example

```bash
set -a
. "$HOME/.vault-gate-client/config.env"
set +a

curl -sS "$VAULT_GATE_URL/capture" \
  -H "Authorization: Bearer $VAULT_GATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "script",
    "title": "Script capture",
    "body": "Markdown body"
  }'
```

## Python example

```python
import json
import os
import urllib.request


def load_env(path):
    values = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    return values


config = load_env(os.path.expanduser("~/.vault-gate-client/config.env"))
payload = json.dumps({
    "source": "python",
    "title": "Python capture",
    "body": "Markdown body",
}).encode("utf-8")

request = urllib.request.Request(
    f"{config['VAULT_GATE_URL']}/capture",
    data=payload,
    headers={
        "Authorization": f"Bearer {config['VAULT_GATE_TOKEN']}",
        "Content-Type": "application/json",
    },
    method="POST",
)

with urllib.request.urlopen(request, timeout=15) as response:
    print(response.read().decode("utf-8"))
```

## Node.js example

```js
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function loadEnv(filePath) {
  const result = {};
  for (const line of fs.readFileSync(filePath, "utf8").split("\n")) {
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const [key, ...rest] = line.split("=");
    result[key] = rest.join("=").replace(/^"|"$/g, "");
  }
  return result;
}

const config = loadEnv(path.join(os.homedir(), ".vault-gate-client/config.env"));

const response = await fetch(`${config.VAULT_GATE_URL}/capture`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${config.VAULT_GATE_TOKEN}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    source: "node",
    title: "Node capture",
    body: "Markdown body",
  }),
});

console.log(await response.json());
```

## Long-running services

For services running on the remote macOS device:

1. Do not hard-code `VAULT_GATE_TOKEN` in source code.
2. Read `~/.vault-gate-client/config.env`.
3. Send new material to `/capture`.
4. Send existing-note changes to `/edit-request`.
5. Log only status, returned path, run id, and errors. Do not log tokens.

Shell services can load the config like this:

```bash
set -a
. "$HOME/.vault-gate-client/config.env"
set +a
```

Then call the API with `$VAULT_GATE_URL` and `$VAULT_GATE_TOKEN`.

