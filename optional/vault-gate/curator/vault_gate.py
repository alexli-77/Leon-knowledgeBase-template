#!/usr/bin/env python3
"""Reference implementation for a server-side Markdown vault gate."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DENIED_PARTS = {".git", ".obsidian", ".trash", ".DS_Store"}
SAFE_SOURCE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


@dataclasses.dataclass(frozen=True)
class GateConfig:
    root: Path
    capture_dir: str = "00_Inbox/Capture"
    pending_dir: str = "00_Inbox/Pending-Review"
    log_dir: str = "99_Meta/automation-log"
    auto_commit: bool = False
    author: str = "Vault Gate <vault-gate@example.com>"


@dataclasses.dataclass(frozen=True)
class GateResult:
    status: str
    decision: str
    path: str | None
    run_id: str
    commit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class GateError(Exception):
    pass


def load_config() -> GateConfig:
    root_raw = os.environ.get("VAULT_GATE_ROOT", "").strip()
    if not root_raw:
        raise GateError("VAULT_GATE_ROOT is required")

    return GateConfig(
        root=Path(root_raw).expanduser().resolve(),
        capture_dir=os.environ.get("VAULT_GATE_CAPTURE_DIR", "00_Inbox/Capture"),
        pending_dir=os.environ.get("VAULT_GATE_PENDING_DIR", "00_Inbox/Pending-Review"),
        log_dir=os.environ.get("VAULT_GATE_LOG_DIR", "99_Meta/automation-log"),
        auto_commit=os.environ.get("VAULT_GATE_AUTO_COMMIT", "false").lower() in {"1", "true", "yes"},
        author=os.environ.get("VAULT_GATE_AUTHOR", "Vault Gate <vault-gate@example.com>"),
    )


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip().lower()).strip("-._")
    return slug[:60] or "capture"


def run_id_for(source: str, body: str) -> str:
    seed = f"{now_utc().isoformat()}:{source}:{body}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:12]


def validate_source(source: str) -> str:
    source = source.strip()
    if not SAFE_SOURCE.match(source):
        raise GateError("source must be 1-64 chars: letters, numbers, dot, colon, dash, underscore")
    return source


def safe_join(root: Path, relative: str) -> Path:
    root = root.resolve()
    if not relative or relative.startswith("/") or "\x00" in relative:
        raise GateError("path must be relative")
    rel_path = Path(relative)
    if any(part in {"", ".", ".."} for part in rel_path.parts):
        raise GateError("path cannot contain empty, current, or parent parts")
    if any(part in DENIED_PARTS or part.startswith(".") for part in rel_path.parts):
        raise GateError("path contains a denied hidden/system segment")
    full = (root / rel_path).resolve()
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise GateError("path escapes vault root") from exc
    return full


def relative_to_root(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def ensure_vault_root(config: GateConfig) -> None:
    if not config.root.exists() or not config.root.is_dir():
        raise GateError(f"vault root does not exist: {config.root}")


def markdown_doc(title: str, body: str, source: str, status: str, run_id: str) -> str:
    created = now_utc().isoformat(timespec="seconds")
    safe_title = title.strip() or "Untitled capture"
    return "\n".join(
        [
            "---",
            "tags: [capture, vault-gate]",
            f"created: {created}",
            f"source: {json.dumps(source, ensure_ascii=True)}",
            f"status: {json.dumps(status, ensure_ascii=True)}",
            f"run_id: {json.dumps(run_id, ensure_ascii=True)}",
            "---",
            "",
            f"# {safe_title}",
            "",
            body.rstrip(),
            "",
        ]
    )


def write_unique(path: Path, content: str, dry_run: bool) -> None:
    if path.exists():
        raise GateError(f"target already exists: {path.name}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_log(config: GateConfig, event: dict[str, Any], dry_run: bool) -> None:
    log_dir = safe_join(config.root, config.log_dir)
    month = now_utc().strftime("%Y-%m")
    log_path = log_dir / f"{month}.md"
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    entry = f"\n- `{now_utc().isoformat(timespec='seconds')}` `{event['run_id']}` `{event['decision']}` `{event.get('path')}`\n  ```json\n  {line}\n  ```\n"
    if dry_run:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(f"# Vault Gate automation log {month}\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def git_commit(config: GateConfig, message: str, dry_run: bool) -> str | None:
    if dry_run or not config.auto_commit:
        return None
    if not (config.root / ".git").exists():
        return None
    subprocess.run(["git", "add", "."], cwd=config.root, check=True)
    status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=config.root)
    if status.returncode == 0:
        return None
    name = config.author.split("<")[0].strip() or "Vault Gate"
    email_match = re.search(r"<([^>]+)>", config.author)
    email = email_match.group(1) if email_match else "vault-gate@example.com"
    subprocess.run(
        [
            "git",
            "-c",
            f"user.name={name}",
            "-c",
            f"user.email={email}",
            "commit",
            "-m",
            message,
        ],
        cwd=config.root,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=config.root, text=True)
    return rev.strip()


def capture(config: GateConfig, source: str, title: str, body: str, dry_run: bool = False) -> GateResult:
    ensure_vault_root(config)
    source = validate_source(source)
    if not body.strip():
        raise GateError("body is required")

    run_id = run_id_for(source, body)
    filename = f"{now_utc().strftime('%Y%m%d-%H%M%S')}-{slugify(title)}-{run_id}.md"
    target = safe_join(config.root, f"{config.capture_dir}/{filename}")
    rel = relative_to_root(target, config.root)
    content = markdown_doc(title, body, source, "inbox", run_id)
    write_unique(target, content, dry_run)

    event = {"run_id": run_id, "decision": "captured", "source": source, "path": rel, "dry_run": dry_run}
    append_log(config, event, dry_run)
    commit = git_commit(config, f"vault-gate: capture {run_id}", dry_run)
    return GateResult("ok", "captured", rel, run_id, commit)


def edit_request(config: GateConfig, source: str, title: str, body: str, dry_run: bool = False) -> GateResult:
    ensure_vault_root(config)
    source = validate_source(source)
    if not body.strip():
        raise GateError("body is required")

    run_id = run_id_for(source, body)
    filename = f"{now_utc().strftime('%Y%m%d-%H%M%S')}-{slugify(title)}-{run_id}.md"
    target = safe_join(config.root, f"{config.pending_dir}/{filename}")
    rel = relative_to_root(target, config.root)
    content = markdown_doc(title, body, source, "pending-review", run_id)
    write_unique(target, content, dry_run)

    event = {"run_id": run_id, "decision": "pending-review", "source": source, "path": rel, "dry_run": dry_run}
    append_log(config, event, dry_run)
    commit = git_commit(config, f"vault-gate: pending review {run_id}", dry_run)
    return GateResult("ok", "pending-review", rel, run_id, commit)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Server-side Markdown vault gate")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("capture", "edit-request"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--source", required=True)
        cmd.add_argument("--title", default="")
        cmd.add_argument("--body", required=True)
        cmd.add_argument("--dry-run", action="store_true")

    check = sub.add_parser("check-path")
    check.add_argument("--path", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config()
        if args.command == "capture":
            result = capture(config, args.source, args.title, args.body, args.dry_run)
        elif args.command == "edit-request":
            result = edit_request(config, args.source, args.title, args.body, args.dry_run)
        else:
            path = safe_join(config.root, args.path)
            result = GateResult("ok", "path-allowed", relative_to_root(path, config.root), "check")
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        return 0
    except GateError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
