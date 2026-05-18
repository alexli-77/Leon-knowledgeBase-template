# Vault Gate curator

`vault_gate.py` is the reference gate implementation. It has no third-party dependencies.

Supported commands:

```bash
python3 vault_gate.py capture --source discord --title "Idea" --body "..."
python3 vault_gate.py edit-request --source hermes --title "Change request" --body "..."
python3 vault_gate.py check-path --path "00_Inbox/Capture/example.md"
```

Environment variables:

- `VAULT_GATE_ROOT`: absolute path to `Private-Vault`
- `VAULT_GATE_CAPTURE_DIR`: relative capture directory, default `00_Inbox/Capture`
- `VAULT_GATE_PENDING_DIR`: relative pending directory, default `00_Inbox/Pending-Review`
- `VAULT_GATE_LOG_DIR`: relative automation log directory, default `99_Meta/automation-log`
- `VAULT_GATE_AUTO_COMMIT`: `true` to commit each successful write
- `VAULT_GATE_AUTHOR`: git author string for auto commits

The implementation only writes new Markdown files and appends an automation log. It does not edit, move, or delete existing notes.

