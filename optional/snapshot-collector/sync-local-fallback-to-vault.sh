#!/usr/bin/env bash
set -euo pipefail

VAULT_ROOT="${VAULT_ROOT:-${1:-$HOME/ObsidianVault}}"
LOCAL_ROOT="$HOME/Library/Application Support/vault-snapshot-collector/snapshots"
VAULT_SNAPSHOT_ROOT="$VAULT_ROOT/_snapshots"

if [[ ! -d "$LOCAL_ROOT" ]]; then
  echo "Local snapshot root not found: $LOCAL_ROOT" >&2
  exit 1
fi

mkdir -p "$VAULT_SNAPSHOT_ROOT"
/usr/bin/rsync -a "$LOCAL_ROOT/" "$VAULT_SNAPSHOT_ROOT/"
echo "synced $LOCAL_ROOT -> $VAULT_SNAPSHOT_ROOT"
