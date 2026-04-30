# Integrations

Setup instructions for the major AI agent hosts. All of them speak
MCP, so the recipe is the same across hosts: install `receipts` with
the `mcp` extra, drop a small JSON block into the host's MCP config,
restart. Done. The agent now has `receipts_audit` /
`receipts_transcribe` / `receipts_research` as native tools.

> **Prerequisite for all of them:** `pip install 'receipts[mcp]'` in
> the same Python environment the host launches subprocesses from.
> Verify `receipts-mcp` is on `PATH`: `which receipts-mcp` (POSIX) /
> `where receipts-mcp` (Windows).
>
> No API keys needed — the default rule-based vetter runs offline.
> `yt-dlp` (the only runtime dependency) is installed automatically.

## Claude Code

**One-liner (recommended):**

```bash
cd <your-project>
receipts install claude-code
```

That writes (or merges into) `.mcp.json` at the project root. Existing
servers (e.g. `tether`) are preserved.

**Manual:** edit `.mcp.json` at the project root (NOT
`.claude/mcp.json` — Claude Code silently ignores that path):

```json
{
  "mcpServers": {
    "receipts": {
      "command": "receipts-mcp"
    }
  }
}
```

> User-scope (global, all projects) lives inside `~/.claude.json` —
> manage via `claude mcp add -s user receipts -- receipts-mcp`, not by
> editing a standalone file.

Restart the Claude Code session. Run `/mcp` — you should see
`receipts` listed with three tools (`receipts_audit`,
`receipts_transcribe`, `receipts_research`).

**Optional but recommended:** drop a Skill so Claude knows when to
use them. Save as `.claude/skills/receipts.md`:

```markdown
---
name: receipts
description: Use when the user (a) shares a YouTube URL and asks "what's in this?" / "is this any good?", or (b) asks to research a topic ("find the best videos on X"). Returns evidence-scored audits and topic-level reading orders.
---

# Skill rules

1. **Single URL** → call `receipts_audit(url, domain="...")`.
   Surface the verdict + 3-5 highest/lowest scoring claims to the
   user. Keep the full report in scratch space for follow-ups.

2. **Topic research** → call
   `receipts_research(topic, n=5, domain="...")`.
   Surface the reading order + the high-evidence claims aggregated
   across the corpus. Tell the user which video to actually watch.

3. **Verbatim transcript** → call `receipts_transcribe(url)`.
   Use only when the user wants the words for citation/search;
   never use this as a substitute for `audit`.

4. **Domain hint:** infer from context. Default `general` is fine
   for most cases. Use `trading` / `health` / `tech` only when the
   user signals it.
```

## Cursor

**Config file:** `~/.cursor/mcp.json` (global) or
`.cursor/mcp.json` (per project, Cursor 0.42+).

```json
{
  "mcpServers": {
    "receipts": {
      "command": "receipts-mcp"
    }
  }
}
```

Restart Cursor. Open the chat sidebar → Settings → MCP — you should
see `receipts` with green status. Try it: paste a YouTube URL into
the Composer and ask *"what's in this?"* — Cursor will call
`receipts_audit` and surface the verdict.

## Cline (VS Code extension)

Cline's MCP config lives in the extension UI (no JSON file):

1. Open the Cline sidebar (icon in VS Code's activity bar).
2. Click the gear icon → **MCP Servers**.
3. Click **Add new MCP Server**.
4. Fill in:
   - **Name:** `receipts`
   - **Command:** `receipts-mcp`
   - **Environment variables:** *(none required)*
5. Save. Restart the Cline session.

Verify by pasting a YouTube URL and saying *"audit this"*.

## Codex CLI (OpenAI)

**Config file:** `~/.codex/mcp.json`.

```json
{
  "mcpServers": {
    "receipts": {
      "command": "receipts-mcp"
    }
  }
}
```

Restart `codex`. The three tools auto-load.

## Continue.dev

**Config file:** `~/.continue/config.yaml` (or
`.continue/config.yaml` per project).

```yaml
mcpServers:
  - name: receipts
    command: receipts-mcp
```

Reload Continue (VS Code: Ctrl/Cmd+Shift+P → "Continue: Reload
Window"). Tools appear under the chat's tool drawer.

## Zed

**Config:** open Zed Settings (`Cmd/Ctrl ,`) and add:

```jsonc
{
  "assistant": {
    "mcp_servers": {
      "receipts": {
        "command": "receipts-mcp"
      }
    }
  }
}
```

Restart the Assistant panel.

## Anthropic SDK / Agent SDK (no MCP host)

Wire receipts as a regular Anthropic tool:

```python
import anthropic
from receipts import audit, research

client = anthropic.Anthropic()

tools = [
    {
        "name": "audit_video",
        "description": (
            "Audit a YouTube video — extract claims, score evidence "
            "quality, return JSON. Use when the user shares a URL and "
            "asks 'what's in this?' or 'is this any good?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url":    {"type": "string"},
                "domain": {"type": "string",
                           "enum": ["general", "trading", "health",
                                    "tech", "science", "legal"]},
            },
            "required": ["url"],
        },
    },
    {
        "name": "research_topic",
        "description": (
            "Find top N YouTube videos on a topic, audit each, "
            "synthesize a cross-video reading-order report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic":  {"type": "string"},
                "n":      {"type": "integer", "default": 5},
                "domain": {"type": "string", "default": "general"},
            },
            "required": ["topic"],
        },
    },
]

def call_tool(name: str, input: dict) -> str:
    if name == "audit_video":
        report = audit(input["url"], domain=input.get("domain", "general"))
        return report.to_markdown()
    if name == "research_topic":
        report = research(input["topic"], n=input.get("n", 5),
                           domain=input.get("domain", "general"))
        return report.to_markdown()
    raise ValueError(f"unknown tool {name}")
```

## Plain Python (no AI required)

```python
from receipts import audit, research

# One video
r = audit("https://youtu.be/<id>")
print(r.verdict)

# Topic research
res = research("LLM agent design patterns", n=5)
for r in res.reading_order():
    print(f"{r.verdict:15} {r.metadata.title}")
print(res.to_markdown())
```

## CI / batch (no AI required)

Audit a list of URLs nightly, save Markdown reports + an index:

```bash
# urls.txt — one URL per line, # comments OK
receipts batch urls.txt --output-dir reports/$(date +%Y-%m-%d)/
```

Or research a topic on cron:

```bash
0 8 * * 1 receipts research "this week in AI" --n 7 \
    -o /var/log/receipts/$(date +%Y-%m-%d)-ai-week.md
```

## Composing with `tether`

Both repos are siblings. Configure both MCP servers in the same
`mcp.json` and your agent can do mobile-driven workflows:

```json
{
  "mcpServers": {
    "tether": {
      "command": "tether-mcp",
      "env": {
        "TELEGRAM_BOT_TOKEN": "...",
        "TELEGRAM_CHAT_ID": "..."
      }
    },
    "receipts": {
      "command": "receipts-mcp"
    }
  }
}
```

Now the user can text the agent from their phone: *"audit
https://youtu.be/abc"* — the agent polls via `tether_poll`, calls
`receipts_audit`, sends the verdict back via `tether_send`. Full
loop, ~15 lines of agent logic.
