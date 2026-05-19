#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Vault Gate macOS client installer

Usage:
  ./client-install.sh install --url URL --token TOKEN
  ./client-install.sh install --config CONFIG_FILE
  ./client-install.sh status
  ./client-install.sh uninstall

Examples:
  ./client-install.sh install \
    --url http://100.113.147.117:8787 \
    --token paste-token-here

  ./client-install.sh status
  vault-capture "Idea title" "Markdown body"
  echo "Markdown body" | vault-capture "Idea title"
  vault-edit-request "Please reorganize notes about X"

Install target:
  ~/.vault-gate-client/config.env
  ~/.local/bin/vault-capture
  ~/.local/bin/vault-edit-request
EOF
}

config_dir="$HOME/.vault-gate-client"
config_file="$config_dir/config.env"
bin_dir="$HOME/.local/bin"

url=""
token=""

read_config_value() {
  local file="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); gsub(/^"|"$/, ""); print; exit}' "$file"
}

parse_install_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --url)
        url="${2:-}"
        shift 2
        ;;
      --token)
        token="${2:-}"
        shift 2
        ;;
      --config)
        local source_config="${2:-}"
        [[ -f "$source_config" ]] || { echo "Config not found: $source_config" >&2; exit 1; }
        url="$(read_config_value "$source_config" VAULT_GATE_URL)"
        token="$(read_config_value "$source_config" VAULT_GATE_TOKEN)"
        shift 2
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
  if [[ -z "$url" || -z "$token" ]]; then
    echo "Both --url and --token are required, or pass --config." >&2
    exit 1
  fi
  url="${url%/}"
}

write_config() {
  mkdir -p "$config_dir"
  chmod 700 "$config_dir"
  {
    printf 'VAULT_GATE_URL=%s\n' "$url"
    printf 'VAULT_GATE_TOKEN=%s\n' "$token"
  } > "$config_file"
  chmod 600 "$config_file"
}

write_command() {
  local name="$1"
  local endpoint="$2"
  local default_title="$3"
  mkdir -p "$bin_dir"
  cat > "$bin_dir/$name" <<EOF
#!/usr/bin/env bash
set -euo pipefail

CONFIG="\${VAULT_GATE_CLIENT_CONFIG:-\$HOME/.vault-gate-client/config.env}"
if [[ ! -f "\$CONFIG" ]]; then
  echo "Missing config: \$CONFIG" >&2
  echo "Run client-install.sh install first." >&2
  exit 1
fi

set -a
. "\$CONFIG"
set +a

title="\${1:-$default_title}"
body="\${2:-}"
if [[ -z "\$body" && ! -t 0 ]]; then
  body="\$(cat)"
fi
if [[ -z "\$body" ]]; then
  body="\$title"
fi

python3 - "\$VAULT_GATE_URL/$endpoint" "\$VAULT_GATE_TOKEN" "\$title" "\$body" <<'PY'
import json
import sys
import urllib.request

url, token, title, body = sys.argv[1:5]
payload = json.dumps({
    "source": "macos",
    "title": title,
    "body": body,
}).encode("utf-8")
request = urllib.request.Request(
    url,
    data=payload,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=15) as response:
        print(response.read().decode("utf-8"))
except Exception as exc:
    print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
    raise SystemExit(1)
PY
EOF
  chmod +x "$bin_dir/$name"
}

install_client() {
  parse_install_args "$@"
  write_config
  write_command "vault-capture" "capture" "Capture"
  write_command "vault-edit-request" "edit-request" "Edit request"
  status
  cat <<EOF

Installed commands:
  $bin_dir/vault-capture
  $bin_dir/vault-edit-request

Add this to your shell profile if ~/.local/bin is not in PATH:
  export PATH="\$HOME/.local/bin:\$PATH"
EOF
}

status() {
  if [[ ! -f "$config_file" ]]; then
    echo "client_config=missing"
    return 1
  fi
  set -a
  # shellcheck disable=SC1090
  . "$config_file"
  set +a
  echo "client_config=$config_file"
  echo "url=$VAULT_GATE_URL"
  curl -sS --max-time 5 "$VAULT_GATE_URL/health" || true
  printf '\n'
}

uninstall_client() {
  rm -f "$bin_dir/vault-capture" "$bin_dir/vault-edit-request"
  echo "Removed client commands. Config kept at $config_file"
}

case "${1:-}" in
  install)
    shift
    install_client "$@"
    ;;
  status)
    status
    ;;
  uninstall)
    uninstall_client
    ;;
  --help|-h|"")
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
