#!/usr/bin/env python3
import json
import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "ObsidianVault"))).expanduser()
SNAPSHOT_DIRNAME = os.environ.get("SNAPSHOT_DIRNAME", "_snapshots")
LOCAL_APP_DIR = Path.home() / "Library" / "Application Support" / "vault-snapshot-collector"
LOCAL_LOG_DIR = Path.home() / "Library" / "Logs" / "vault-snapshot-collector"
LOCAL_SNAPSHOT_ROOT = LOCAL_APP_DIR / "snapshots"
TZ = ZoneInfo(os.environ.get("SNAPSHOT_TZ", "America/Toronto"))
TAB_DELIM = " ||| "


def run(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path, text):
    path.write_text(text, encoding="utf-8")


def osascript(script):
    return run(["/usr/bin/osascript", "-e", script], timeout=8)


def parse_tab_lines(text, browser):
    tabs = []
    for line in text.splitlines():
        parts = line.split(TAB_DELIM, 2)
        if len(parts) < 2:
            continue
        tabs.append({"browser": browser, "title": parts[0], "url": parts[1]})
    return tabs


def collect_chrome_tabs():
    script = r'''
tell application "System Events"
  if not (exists process "Google Chrome") then return ""
end tell
tell application "Google Chrome"
  set out to ""
  repeat with w in windows
    repeat with t in tabs of w
      set out to out & (title of t as text) & " ||| " & (URL of t as text) & linefeed
    end repeat
  end repeat
  return out
end tell
'''
    result = osascript(script)
    return parse_tab_lines(result["stdout"], "Google Chrome") if result["ok"] else []


def collect_safari_tabs():
    script = r'''
tell application "System Events"
  if not (exists process "Safari") then return ""
end tell
tell application "Safari"
  set out to ""
  repeat with w in windows
    repeat with t in tabs of w
      set out to out & (name of t as text) & " ||| " & (URL of t as text) & linefeed
    end repeat
  end repeat
  return out
end tell
'''
    result = osascript(script)
    return parse_tab_lines(result["stdout"], "Safari") if result["ok"] else []


def collect_visible_apps():
    script = 'tell application "System Events" to get name of every process whose background only is false'
    result = osascript(script)
    if not result["ok"]:
        return []
    return [item.strip() for item in result["stdout"].strip().split(",") if item.strip()]


def collect_processes():
    result = run(["/bin/ps", "aux"], timeout=8)
    needles = [
        "Codex",
        "claude",
        "Claude",
        "Discord",
        "Google Chrome",
        "Obsidian",
        "Feishu",
        "Lark",
        "Tailscale",
    ]
    lines = [line for line in result["stdout"].splitlines() if any(n in line for n in needles)]
    return "\n".join(lines) + ("\n" if lines else "")


def recent_files(root, limit=80):
    root = Path(root).expanduser()
    if not root.exists():
        return []
    rows = []
    for path in root.rglob("*"):
        try:
            if path.is_file():
                stat = path.stat()
                rows.append(
                    {
                        "path": str(path),
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime, TZ).isoformat(),
                    }
                )
        except Exception:
            continue
    rows.sort(key=lambda row: row["mtime"], reverse=True)
    return rows[:limit]


def refresh_latest(snapshot_dir, latest_root):
    if latest_root.exists():
        shutil.rmtree(latest_root)
    latest_root.mkdir(parents=True, exist_ok=True)
    for path in snapshot_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, latest_root / path.name)


def choose_snapshot_root():
    vault_snapshot_root = VAULT_ROOT / SNAPSHOT_DIRNAME
    try:
        vault_snapshot_root.mkdir(parents=True, exist_ok=True)
        probe = vault_snapshot_root / ".write-test"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return vault_snapshot_root, VAULT_ROOT / "_automation" / "snapshot-collector" / "logs", "vault"
    except Exception:
        LOCAL_SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
        LOCAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
        return LOCAL_SNAPSHOT_ROOT, LOCAL_LOG_DIR, "local-fallback"


def main():
    now = datetime.now(TZ)
    snapshot_root, log_dir, storage = choose_snapshot_root()
    snapshot_dir = snapshot_root / "daily" / now.strftime("%Y-%m-%d") / now.strftime("%H%M%S")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "created_at": now.isoformat(),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "vault_root": str(VAULT_ROOT),
        "snapshot_dir": str(snapshot_dir),
        "storage": storage,
    }

    tabs = collect_chrome_tabs() + collect_safari_tabs()

    write_json(snapshot_dir / "metadata.json", metadata)
    write_json(snapshot_dir / "browser-tabs.json", tabs)
    write_json(snapshot_dir / "visible-apps.json", collect_visible_apps())
    write_text(snapshot_dir / "processes.txt", collect_processes())
    write_json(snapshot_dir / "codex-recent-files.json", recent_files("~/.codex", limit=120))
    write_json(snapshot_dir / "codex-app-recent-files.json", recent_files("~/Library/Application Support/Codex", limit=120))
    write_json(snapshot_dir / "claude-recent-files.json", recent_files("~/.claude/projects", limit=120))

    summary = [
        f"# Snapshot {now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        f"- Host: `{metadata['host']}`",
        f"- Storage: `{storage}`",
        f"- Browser tabs: {len(tabs)}",
        f"- Snapshot dir: `{snapshot_dir}`",
        "",
        "## Browser Tabs",
        "",
    ]
    for tab in tabs[:80]:
        summary.append(f"- [{tab['title']}]({tab['url']}) ({tab['browser']})")
    if len(tabs) > 80:
        summary.append(f"- ... {len(tabs) - 80} more")
    write_text(snapshot_dir / "summary.md", "\n".join(summary) + "\n")

    refresh_latest(snapshot_dir, snapshot_root / "latest")
    with (log_dir / "collect_snapshot.log").open("a", encoding="utf-8") as log:
        log.write(f"{now.isoformat()} wrote {snapshot_dir}\n")

    print(snapshot_dir)


if __name__ == "__main__":
    main()
