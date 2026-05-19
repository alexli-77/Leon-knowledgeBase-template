#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Vault Gate installer

Usage:
  ./install.sh install
  ./install.sh restart
  ./install.sh status
  ./install.sh client-config

Commands:
  install        Create/update env, launchd service, and Hermes skill
  restart        Restart the launchd service
  status         Show service and health status without secrets
  client-config  Print the remote macOS URL and token

Environment overrides:
  VAULT_GATE_ROOT=/absolute/path/to/Private-Vault
  VAULT_GATE_PORT=8787
  VAULT_GATE_HOST=100.x.y.z
  VAULT_GATE_ENV=$HOME/.vault-gate/vault-gate.env
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
vault_root="${VAULT_GATE_ROOT:-$(cd "$script_dir/../.." && pwd)}"
env_file="${VAULT_GATE_ENV:-$HOME/.vault-gate/vault-gate.env}"
port="${VAULT_GATE_PORT:-8787}"
label="com.leon.vault-capture-api"
plist="$HOME/Library/LaunchAgents/$label.plist"
api_script="$script_dir/capture-api/app.py"
hermes_skill_dir="$HOME/.hermes/skills/note-taking/vault-gate"

tailscale_ip() {
  if [[ -n "${VAULT_GATE_HOST:-}" ]]; then
    printf '%s\n' "$VAULT_GATE_HOST"
    return
  fi
  if command -v tailscale >/dev/null 2>&1; then
    tailscale ip -4 2>/dev/null | head -n 1
  fi
}

existing_value() {
  local key="$1"
  [[ -f "$env_file" ]] || return 0
  awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); gsub(/^"|"$/, ""); print; exit}' "$env_file"
}

generate_token() {
  local existing
  existing="$(existing_value VAULT_GATE_TOKEN || true)"
  if [[ -n "$existing" && "$existing" != replace-* ]]; then
    printf '%s\n' "$existing"
    return
  fi
  openssl rand -hex 32
}

write_env() {
  local host token
  host="$(tailscale_ip)"
  if [[ -z "$host" ]]; then
    echo "Could not detect Tailscale IP. Set VAULT_GATE_HOST manually." >&2
    exit 1
  fi
  token="$(generate_token)"
  mkdir -p "$(dirname "$env_file")" "$HOME/.vault-gate/logs"
  chmod 700 "$(dirname "$env_file")"
  {
    printf 'VAULT_GATE_ROOT=%s\n' "$vault_root"
    printf 'VAULT_GATE_CAPTURE_DIR=%s\n' '00_Inbox/Capture'
    printf 'VAULT_GATE_PENDING_DIR=%s\n' '00_Inbox/Pending-Review'
    printf 'VAULT_GATE_LOG_DIR=%s\n' '99_Meta/automation-log'
    printf 'VAULT_GATE_HOST=%s\n' "$host"
    printf 'VAULT_GATE_PORT=%s\n' "$port"
    printf 'VAULT_GATE_URL=http://%s:%s\n' "$host" "$port"
    printf 'VAULT_GATE_TOKEN=%s\n' "$token"
    printf 'VAULT_GATE_AUTHOR="%s"\n' 'Vault Gate <vault-gate@example.com>'
    printf 'VAULT_GATE_AUTO_COMMIT=%s\n' 'true'
  } > "$env_file"
  chmod 600 "$env_file"
}

write_launchd() {
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>bash</string>
    <string>-lc</string>
    <string>set -a; . "$env_file"; set +a; exec python3 "$api_script" --host "\$VAULT_GATE_HOST" --port "\$VAULT_GATE_PORT"</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$HOME/.vault-gate/logs/capture-api.out.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/.vault-gate/logs/capture-api.err.log</string>
</dict>
</plist>
EOF
  chmod 644 "$plist"
}

install_hermes_skill() {
  if [[ -d "$HOME/.hermes/skills" ]]; then
    mkdir -p "$hermes_skill_dir"
    cp "$script_dir/hermes-skill/SKILL.md" "$hermes_skill_dir/SKILL.md"
    if [[ -f "$HOME/.hermes/.env" ]]; then
      local tmp
      tmp="$(mktemp)"
      awk '!/^VAULT_GATE_URL=/ && !/^VAULT_GATE_TOKEN=/' "$HOME/.hermes/.env" > "$tmp"
      . "$env_file"
      printf 'VAULT_GATE_URL=%s\n' "$VAULT_GATE_URL" >> "$tmp"
      printf 'VAULT_GATE_TOKEN=%s\n' "$VAULT_GATE_TOKEN" >> "$tmp"
      mv "$tmp" "$HOME/.hermes/.env"
      chmod 600 "$HOME/.hermes/.env"
    fi
  fi
}

restart_service() {
  launchctl bootout "gui/$UID" "$plist" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$plist"
  launchctl kickstart -k "gui/$UID/$label"
}

status() {
  if launchctl print "gui/$UID/$label" >/dev/null 2>&1; then
    launchctl print "gui/$UID/$label" | awk -F'= ' '/state =|pid =|runs =/{print}'
  else
    echo "launchd: not loaded"
  fi
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
    printf 'url=%s\n' "$VAULT_GATE_URL"
    local attempt
    for attempt in 1 2 3 4 5; do
      if curl -sS --max-time 5 "$VAULT_GATE_URL/health"; then
        printf '\n'
        return
      fi
      sleep 1
    done
    printf '\n'
  fi
}

client_config() {
  if [[ ! -f "$env_file" ]]; then
    echo "Missing env file. Run: ./install.sh install" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  . "$env_file"
  set +a
  cat <<EOF
URL:
$VAULT_GATE_URL/capture

Edit request URL:
$VAULT_GATE_URL/edit-request

Authorization header:
Bearer $VAULT_GATE_TOKEN

Content-Type:
application/json

Example body:
{"source":"macos","title":"标题","body":"正文"}
EOF
}

install() {
  mkdir -p "$vault_root/00_Inbox/Capture" "$vault_root/00_Inbox/Pending-Review" "$vault_root/99_Meta/automation-log"
  write_env
  write_launchd
  install_hermes_skill
  restart_service
  status
}

case "${1:-}" in
  install)
    install
    ;;
  restart)
    write_launchd
    restart_service
    status
    ;;
  status)
    status
    ;;
  client-config)
    client_config
    ;;
  --help|-h|"")
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
