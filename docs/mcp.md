# MCP server

`receipts` ships an MCP (Model Context Protocol) server that exposes
the audit pipeline as native tools to any MCP-aware AI client — Claude
Code, Cursor, Cline, Codex, etc.

## Why MCP?

Most agents today, when given a YouTube URL, can only:
1. Acknowledge the URL.
2. Call a generic web-search to find a summary.

With `receipts-mcp` configured, the agent gains two native tools that
turn a YouTube URL into a structured, evidence-scored Markdown report
in one tool call — no glue code, no shelling out.

## Install

```bash
pip install 'receipts[mcp]'    # adds the `mcp` package
```

This installs an additional console script: `receipts-mcp`.

## Configure Claude Code

Edit `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "receipts": {
      "command": "receipts-mcp"
    }
  }
}
```

No env vars needed; the audit pipeline uses only `yt-dlp` (no API
keys). Restart the session; verify with `/mcp`.

## Tools exposed

### `receipts_audit(url, domain="general", max_transcript_chars=6000) -> str`

Audit a YouTube video. Extract claims, score by evidence quality,
return a JSON-encoded report.

```
> receipts_audit(url="https://youtu.be/0L6Rcgp6j7Y", domain="trading")
{
  "metadata": {
    "video_id": "0L6Rcgp6j7Y",
    "title": "Four Price Action Secrets ...",
    "channel": "TradingLab",
    "duration_pretty": "8m 10s",
    ...
  },
  "verdict": "LOW_EVIDENCE",
  "claims_count": 24,
  "claims": [
    {"text": "...", "has_number": true, "has_source": false, ...},
    ...
  ],
  "transcript_excerpt": "first 6000 chars of cleaned transcript",
  "transcript_truncated": true,
  ...
}
```

The `domain` parameter is a hint: passes through to the vetter, useful
when you eventually plug in a domain-specialized vetter (TradingVetter,
HealthVetter, etc.).

`max_transcript_chars` caps the returned transcript so the agent's
context budget isn't blown on long videos. Default 6000 (~900 words).

### `receipts_transcribe(url, max_chars=20000) -> str`

Fetch + clean the transcript only — no audit. Use when the user wants
the words verbatim (citation, search, downstream LLM step).

```
> receipts_transcribe(url="https://youtu.be/0L6Rcgp6j7Y")
{
  "video_id": "0L6Rcgp6j7Y",
  "title": "Four Price Action Secrets ...",
  "channel": "TradingLab",
  "duration_seconds": 490,
  "word_count": 1544,
  "text": "price action probably one of the most important...",
  "truncated": false
}
```

## Example agent flow

User shares a YouTube URL:

```
User: "What's in https://youtu.be/abc123? Worth my time?"

Claude (with receipts MCP):
  → receipts_audit(url="https://youtu.be/abc123", domain="general")
  ← {"verdict": "MIXED", "claims_count": 14, ...}
  → "Audit shows MIXED evidence — 14 claims, 6 with numbers, 2 cite
     sources. Strongest claim: ... Weakest: ... Worth a skim if
     you're interested in the topic; not a citable source."
```

The whole flow is one tool call + one structured response. No
prompt-stuffing transcripts, no manual "let me get the transcript
first then summarize then evaluate"-style 3-step dance.

## Combining with `tether`

The two servers compose cleanly:

```json
{
  "mcpServers": {
    "tether": {
      "command": "tether-mcp",
      "env": {"TELEGRAM_BOT_TOKEN": "...", "TELEGRAM_CHAT_ID": "..."}
    },
    "receipts": {
      "command": "receipts-mcp"
    }
  }
}
```

Now your agent can:

```
User (in Telegram): "Quick audit on https://youtu.be/abc"

Claude (background daemon detects new tether msg):
  → tether_poll(timeout_seconds=30)
  ← [{"text": "Quick audit on https://...", ...}]
  → tether_send(text="On it.")                                    # ack-first
  → receipts_audit(url="https://youtu.be/abc", domain="general")  # work
  ← {"verdict": "LOW_EVIDENCE", ...}
  → tether_send(text="Verdict LOW_EVIDENCE. 8 claims, 1 with a number,
                       0 with sources. Skim only.")
```

Two MCP servers, ~15 lines of agent logic, full mobile-driven
video-audit workflow.

## Troubleshooting

### `mcp` import error at start

You installed `receipts` without the `mcp` extra:

```bash
pip install 'receipts[mcp]'
```

### `FetchError: yt-dlp ...`

Same as the CLI — see [troubleshooting.md](troubleshooting.md). The
MCP server returns `{"error": "..."}` JSON instead of crashing, so
the agent can handle it gracefully.

### MCP server doesn't appear in /mcp

Check `receipts-mcp` resolves on PATH. If you're in a venv, give the
host the full path:

```json
"command": "/Users/you/.venvs/agents/bin/receipts-mcp"
```
