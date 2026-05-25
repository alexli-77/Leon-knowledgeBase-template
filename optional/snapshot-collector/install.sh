#!/usr/bin/env bash
set -euo pipefail

VAULT_ROOT="${1:-$HOME/ObsidianVault}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/Library/Application Support/vault-snapshot-collector"
LOG_DIR="$HOME/Library/Logs/vault-snapshot-collector"
PLIST="$HOME/Library/LaunchAgents/local.vault-snapshot.plist"

mkdir -p "$APP_DIR" "$LOG_DIR" "$HOME/Library/LaunchAgents"
cp "$SCRIPT_DIR/collect_snapshot.py" "$APP_DIR/collect_snapshot.py"
chmod +x "$APP_DIR/collect_snapshot.py"

sed \
  -e "s|__VAULT_ROOT__|$VAULT_ROOT|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  -e "s|__LOG_DIR__|$LOG_DIR|g" \
  "$SCRIPT_DIR/launchd/local.vault-snapshot.plist.template" > "$PLIST"

launchctl bootout "gui/$(id -u)/local.vault-snapshot" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed hourly snapshot collector."
echo "Vault root: $VAULT_ROOT"
echo "LaunchAgent: $PLIST"
