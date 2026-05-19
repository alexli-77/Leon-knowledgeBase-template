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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DENIED_PARTS = {".git", ".obsidian", ".trash", ".DS_Store"}
SAFE_SOURCE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
SAFE_ROUTE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
SAFE_MODE = {"append", "create", "upsert"}


@dataclasses.dataclass(frozen=True)
class GateConfig:
    root: Path
    capture_dir: str = "00_Inbox/Capture"
    pending_dir: str = "00_Inbox/Pending-Review"
    log_dir: str = "99_Meta/automation-log"
    timezone: str = "UTC"
    route_map: dict[str, Any] = dataclasses.field(default_factory=dict)
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

    routes_raw = os.environ.get("VAULT_GATE_ROUTES_JSON", "").strip()
    route_map: dict[str, Any] = {}
    if routes_raw:
        try:
            loaded = json.loads(routes_raw)
            if not isinstance(loaded, dict):
                raise ValueError("VAULT_GATE_ROUTES_JSON must be a JSON object")
            route_map = loaded
        except ValueError as exc:
            raise GateError(f"invalid VAULT_GATE_ROUTES_JSON: {exc}") from exc

    return GateConfig(
        root=Path(root_raw).expanduser().resolve(),
        capture_dir=os.environ.get("VAULT_GATE_CAPTURE_DIR", "00_Inbox/Capture"),
        pending_dir=os.environ.get("VAULT_GATE_PENDING_DIR", "00_Inbox/Pending-Review"),
        log_dir=os.environ.get("VAULT_GATE_LOG_DIR", "99_Meta/automation-log"),
        timezone=os.environ.get("VAULT_GATE_TIMEZONE", "UTC"),
        route_map=route_map,
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


def validate_route(route: str) -> str:
    route = route.strip()
    if not SAFE_ROUTE.match(route):
        raise GateError("route must be 1-64 chars: letters, numbers, dot, colon, dash, underscore")
    return route


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


def append_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# {path.stem}\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


def append_log(config: GateConfig, event: dict[str, Any], dry_run: bool) -> str | None:
    log_dir = safe_join(config.root, config.log_dir)
    month = now_utc().strftime("%Y-%m")
    log_path = log_dir / f"{month}.md"
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    entry = f"\n- `{now_utc().isoformat(timespec='seconds')}` `{event['run_id']}` `{event['decision']}` `{event.get('path')}`\n  ```json\n  {line}\n  ```\n"
    if dry_run:
        return None
    log_dir.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(f"# Vault Gate automation log {month}\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)
    return relative_to_root(log_path, config.root)


def git_root(config: GateConfig) -> Path | None:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(config.root), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return Path(output.strip())
    except subprocess.CalledProcessError:
        return None


def git_commit(config: GateConfig, message: str, dry_run: bool, paths: list[str]) -> str | None:
    if dry_run or not config.auto_commit:
        return None
    repo = git_root(config)
    if repo is None:
        return None
    absolute_paths = [str(safe_join(config.root, path)) for path in paths]
    subprocess.run(["git", "add", *absolute_paths], cwd=repo, check=True)
    status = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *absolute_paths], cwd=repo)
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
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo, text=True)
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
    log_rel = append_log(config, event, dry_run)
    commit_paths = [rel] + ([log_rel] if log_rel else [])
    commit = git_commit(config, f"vault-gate: capture {run_id}", dry_run, commit_paths)
    return GateResult("ok", "captured", rel, run_id, commit)


def local_now(config: GateConfig) -> dt.datetime:
    try:
        zone = ZoneInfo(config.timezone)
    except ZoneInfoNotFoundError:
        zone = dt.timezone.utc
    return dt.datetime.now(zone)


def default_route_map() -> dict[str, Any]:
    return {
        "daily": {"mode": "append", "path": "10_Daily/{year}/{date}.md"},
        "ideas": {"mode": "append", "path": "30_Ideas/_inbox.md"},
        "projects": {"mode": "append", "path": "40_Projects/_inbox.md"},
        "resources": {"mode": "append", "path": "90_Resources/_inbox.md"},
        "people": {"mode": "append", "path": "80_People/_inbox.md"},
        "log": {"mode": "append", "path": "99_Meta/automation-log/{year_month}.md"},
    }


def route_spec(config: GateConfig, route: str) -> dict[str, Any]:
    routes = config.route_map or default_route_map()
    spec = routes.get(route)
    if spec is None:
        allowed = ", ".join(sorted(routes))
        raise GateError(f"unknown route: {route}. Allowed routes: {allowed}")
    if isinstance(spec, str):
        spec = {"path": spec, "mode": "append"}
    if not isinstance(spec, dict):
        raise GateError(f"invalid route spec for {route}")
    path_template = str(spec.get("path", "")).strip()
    mode = str(spec.get("mode", "append")).strip().lower()
    if not path_template:
        raise GateError(f"route {route} has no path")
    if mode not in SAFE_MODE:
        raise GateError(f"route {route} has invalid mode: {mode}")
    return {"path": path_template, "mode": mode}


def render_route_path(config: GateConfig, route: str, title: str, run_id: str) -> str:
    now = local_now(config)
    title_slug = slugify(title)
    values = {
        "route": route,
        "title_slug": title_slug,
        "slug": title_slug,
        "run_id": run_id,
        "date": now.strftime("%Y-%m-%d"),
        "datetime": now.strftime("%Y%m%d-%H%M%S"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
        "year_month": now.strftime("%Y-%m"),
    }
    return route_spec(config, route)["path"].format(**values)


def routed_entry(config: GateConfig, source: str, route: str, title: str, body: str, run_id: str) -> str:
    now = local_now(config).isoformat(timespec="seconds")
    heading = title.strip() or f"{route} {now}"
    return "\n".join(
        [
            "",
            f"## {heading}",
            "",
            f"- source: `{source}`",
            f"- route: `{route}`",
            f"- created: `{now}`",
            f"- run_id: `{run_id}`",
            "",
            body.rstrip(),
            "",
        ]
    )


def write_route(
    config: GateConfig,
    source: str,
    route: str,
    title: str,
    body: str,
    dry_run: bool = False,
) -> GateResult:
    ensure_vault_root(config)
    source = validate_source(source)
    route = validate_route(route)
    if not body.strip():
        raise GateError("body is required")

    run_id = run_id_for(f"{source}:{route}", body)
    spec = route_spec(config, route)
    target = safe_join(config.root, render_route_path(config, route, title, run_id))
    rel = relative_to_root(target, config.root)
    content = routed_entry(config, source, route, title, body, run_id)

    if spec["mode"] == "append":
        append_text(target, content, dry_run)
    elif spec["mode"] == "create":
        write_unique(target, markdown_doc(title, body, source, "routed", run_id), dry_run)
    else:
        if target.exists():
            append_text(target, content, dry_run)
        else:
            write_unique(target, markdown_doc(title, body, source, "routed", run_id), dry_run)

    event = {
        "run_id": run_id,
        "decision": "routed-write",
        "source": source,
        "route": route,
        "path": rel,
        "mode": spec["mode"],
        "dry_run": dry_run,
    }
    log_rel = append_log(config, event, dry_run)
    commit_paths = [rel] + ([log_rel] if log_rel else [])
    commit = git_commit(config, f"vault-gate: write {route} {run_id}", dry_run, commit_paths)
    return GateResult("ok", "routed-write", rel, run_id, commit)


def read_file(config: GateConfig, path: str) -> dict[str, Any]:
    """Return the raw content of a vault file. Path must be relative to vault root.

    Only regular files are allowed. Hidden/system segments and paths outside
    the vault root are rejected by safe_join.
    """
    ensure_vault_root(config)
    target = safe_join(config.root, path)
    if not target.exists():
        raise GateError(f"file not found: {path}")
    if not target.is_file():
        raise GateError(f"path is not a file: {path}")
    rel = relative_to_root(target, config.root)
    content = target.read_text(encoding="utf-8")
    return {"status": "ok", "path": rel, "content": content}


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
    log_rel = append_log(config, event, dry_run)
    commit_paths = [rel] + ([log_rel] if log_rel else [])
    commit = git_commit(config, f"vault-gate: pending review {run_id}", dry_run, commit_paths)
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

    write = sub.add_parser("write")
    write.add_argument("--source", required=True)
    write.add_argument("--route", required=True)
    write.add_argument("--title", default="")
    write.add_argument("--body", required=True)
    write.add_argument("--dry-run", action="store_true")

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
        elif args.command == "write":
            result = write_route(config, args.source, args.route, args.title, args.body, args.dry_run)
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
