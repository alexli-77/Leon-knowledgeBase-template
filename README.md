# Leon Knowledge Base Template

[English](README.md) | [中文](README.zh.md)

A personal knowledge-base template built on **Obsidian + Claude Code**.
PARA variant + numeric prefixes + MOC files + routing rules + a `/record` skill — making "write it down" a one-line command.

## Who this repo is for

A good fit if:
- You use Obsidian for long-term knowledge
- You use Claude Code as your workstation
- You want zero-friction capture (one line `/record xxx` → auto-filed in the right folder)

Not for you if:
- You just want a notes template and don't want to touch Claude Code (you can still use the `templates/Private-Vault` portion alone)

## Architecture at a glance

```
Your Vault/
├── Private-Vault/          ← personal, not pushed
│   ├── 00_Inbox/           ← inbox / capture
│   ├── 10_Daily/           ← daily notes
│   ├── 20_PhD/             ← PhD-related (or replace with your main work)
│   ├── 30_Work/            ← work / business
│   ├── 40_Apps/            ← side-project apps
│   ├── 50_Content/         ← content / publishing workshop
│   ├── 60_Hobby/           ← hobbies (sports / games / music / etc.)
│   ├── 70_Areas/           ← long-term areas of focus
│   ├── 80_People/          ← personal CRM
│   ├── 90_Resources/       ← reusable resources
│   ├── 95_Archive/         ← archive
│   └── 99_Meta/            ← metadata + management
│       ├── routing.md      ← routing rules for /record
│       ├── watch-list.md   ← follow-up overview (aggregates by `status` field)
│       ├── todos.md        ← small-grain todos (outside OKR scope)
│       ├── done.md         ← archived done items (segmented by month)
│       └── subscriptions.md ← subscription tracking (paid services, expiry dates)
└── Public-Vault/           ← public area (blog, paper notes)
```

How the pieces connect:

1. **`99_Meta/routing.md`** — maps "keywords / content features" to "which file this should go in"
2. **`~/.claude/skills/record/SKILL.md`** — Claude Code global skill; on `/record <content>` it reads routing.md, then decides where to write
3. **Change rules by editing `routing.md` only** — the skill re-reads it every time, no code changes needed

## Quick start

```bash
# 1. clone
git clone <this-repo> && cd leon-knowledgeBase-template

# 2. Deploy to your location (default ~/ObsidianVault)
./setup.sh ~/ObsidianVault

# 3. Install the /record skill (requires Claude Code)
./setup.sh --install-skill

# 4. Open both Vaults in Obsidian
# 5. Try it in Claude Code
/record Learned X today
```

## About the original author

This template is the skeleton Leon (CS PhD candidate at Université de Montréal) extracted from his own vault. Some sub-folders in the original vault are personal:

- `20_PhD` — the author is a PhD student; the original has Research-Logs / Advisor-Meetings / Drafts / Defense. Non-academic users can rename it to `20_Main` (your main work) or delete it.
- `30_Work` — originally `30_Injunction-Practice` (the author's legal business); generalized to `30_Work` in the template.
- `60_Hobby` — originally `60_Badminton` (the author plays badminton). Rename it to your own hobby.
- `50_Content` — content / publishing workshop. Delete if you don't create content.

**These folders are kept because the skeleton (`_MOC.md` + routing-rule logic) transfers well.** Use as-is or remix — up to you.

## Design principles

- `folder = where it is` — folders are the categorization; don't invent complex tag systems
- `_MOC.md = the manual for each folder` — first thing future-you sees when opening a folder
- `routing.md = single source of truth` — when rules change, only one file changes
- `/record is explicit` — no guessing, no interruption
- **Inbox is the fallback** — if no rule matches, drop in Inbox and process on Sunday
- **Status as an orthogonal dimension** — group by content in folders, aggregate by `status` frontmatter into `watch-list.md`

## Handling "things that need periodic follow-up"

Knowledge-base folders are organized by **content type** (PhD / Content / Hobby / ...), but some notes need to be managed **by status**:
project ideas waiting for a trigger, side businesses you haven't decided to start, open-source projects you're watching ...

This template solves it with frontmatter:

```yaml
---
status: watching | considering | active | done | abandoned
priority: low | medium | high
next-review: YYYY-MM-DD
review-cadence: weekly | biweekly | monthly | quarterly
trigger-condition: "what condition triggers a start"
created: YYYY-MM-DD
---
```

Notes still go to the content folder they belong to (e.g., `70_Areas/{area}/` or `50_Content/Ideas/`),
then sync a link to the corresponding section of `99_Meta/watch-list.md`.

Each weekly review, scan the watch-list to decide status changes.
Full spec: see the "Project / Idea status convention" section in `templates/Private-Vault/99_Meta/routing.md.template`.

## Companion skill

This template stands on its own — if all you want is "PARA-organized + `/record` one-shot capture" in Obsidian, you're done.

If you also use Claude Code for OKR / weekly review, here's the companion skill:

> **[life-review-os](https://github.com/alexli-77/life-review-os)** — Life Review OS
>
> A Claude Skill that turns "weekly planning / bi-weekly retro / quarterly direction check" into an automated workflow.
> Reads your Lark (Feishu) Weekly doc, compares plan vs. actual, generates next week's plan, writes it back.
>
> With vault integration enabled, it persists two kinds of data into this template's `99_Meta/`:
> - **watch-list decisions** (auto-scanned by frontmatter status on every review)
> - **OKR metadata** (deadline / phantom status structured fields, written to `99_Meta/okr-metadata.yaml`)
>
> Not bound to this template — any markdown notes directory works as a vault. This is just the out-of-the-box option that already has full PARA structure + watch-list dataview view.

## License

MIT. Use, modify, distribute — freely.

## Contribution flow

The right way to use this is to fork and remix into your own life. If a routing rule or `_MOC` pattern turns out to be worth sharing, PR welcome.
