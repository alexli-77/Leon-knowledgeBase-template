# Snapshot Collector

Optional macOS LaunchAgent for collecting lightweight workstation context into a vault.

It is designed for a setup where one machine is used for daily work and another
machine or service reads stable snapshot files from the vault.

## What It Collects

- Chrome and Safari tab titles and URLs, when available.
- Visible macOS applications.
- A filtered process list for common work tools.
- Recent Codex and Claude file indexes.
- Basic host metadata.
- A human-readable `summary.md`.

It does not copy raw chat logs, browser databases, tokens, cookies, or app
configuration files.

## Snapshot Layout

The collector writes:

```text
_snapshots/
├── daily/YYYY-MM-DD/HHMMSS/
│   ├── metadata.json
│   ├── browser-tabs.json
│   ├── visible-apps.json
│   ├── processes.txt
│   ├── codex-recent-files.json
│   ├── codex-app-recent-files.json
│   ├── claude-recent-files.json
│   └── summary.md
└── latest/
    └── ... copy of newest snapshot files
```

If the LaunchAgent cannot write to the vault path, it falls back to:

```text
~/Library/Application Support/vault-snapshot-collector/snapshots
```

You can sync that fallback directory into the vault with
`sync-local-fallback-to-vault.sh`.

## Install

```bash
cd optional/snapshot-collector
./install.sh /path/to/your/vault
```

The installer creates:

- `~/Library/Application Support/vault-snapshot-collector/collect_snapshot.py`
- `~/Library/LaunchAgents/local.vault-snapshot.plist`
- `~/Library/Logs/vault-snapshot-collector/`

The default interval is once per hour while the Mac is awake. It does not wake a
sleeping Mac. Missed runs are skipped.

## Manual Run

```bash
VAULT_ROOT=/path/to/your/vault python3 collect_snapshot.py
```

## Sync Fallback Data

```bash
VAULT_ROOT=/path/to/your/vault ./sync-local-fallback-to-vault.sh
```
