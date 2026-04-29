# Why receipts exists

## Today's meta-challenge: the content firehose

YouTube has roughly **500 hours uploaded per minute**. A meaningful
slice is "expert" content — finance, health, AI, productivity, legal,
political. Most of it is **unfalsifiable confidence wearing the
costume of expertise**: no quantified evidence, no sources, no sample
sizes, no out-of-sample data, no conflicts-of-interest disclosed —
just *trust me bro* delivered with a thumbnail and a confident voice.

Two existing approaches both fail at scale:

- **Watch the whole video.** Doesn't scale. You can't evaluate 50
  videos a week this way, and most aren't worth a 30-minute commitment
  in the first place.

- **Use a summarizer / NotebookLM-style tool.** These *paraphrase* the
  unfalsifiable claim into something that *sounds* concrete. They make
  the bad content *more* believable, not less. The summary smooths
  over the speaker's missing receipts.

AI agents that watch videos for users do the same thing — they
summarize, they don't audit. There's no fast filter for *"is this
person actually showing the receipts?"*

That's the problem `receipts` solves.

## What receipts does

Receipts is a Python package + CLI + MCP server that takes any
YouTube URL and produces a **brutally honest evidence audit** — not a
summary.

The pipeline:

```
URL → yt-dlp captions → cleaned transcript → claim extraction
                                            → per-claim evidence scoring
                                            → verdict bucketing
                                            → Markdown report
```

The report has a **claims table**: for every claim the speaker makes,
three boolean flags:

- **`has_number`** — does the claim contain a quantitative figure?
  `5%`, `1.5x`, `n=42`, `$1500`, `Sharpe 2.1`. (Or is it pure rhetoric?)

- **`has_source`** — does it cite something? `study`, `paper`,
  `audited statement`, `OOS`, `win-rate`, `sample size`. (Or just
  "everyone knows…"?)

- **`is_testable`** — is it stated as a rule with conditions? "When
  X, do Y." (Or is it a vibe — "the market always rewards patience"?)

A verdict bucket aggregates: `HIGH_EVIDENCE` / `MIXED` /
`LOW_EVIDENCE` / `UNSUPPORTED`.

**Receipts refuses to paraphrase.** The "summary" section of the
report is literally the first 800 characters of the transcript,
verbatim. The point is to *not* smooth over what the speaker actually
said.

## Three modes

### `audit` — single video

```bash
receipts audit https://youtu.be/abc --domain trading -o audit.md
```

One Markdown report. Use as a pre-watch filter (30 seconds vs 30
minutes), or to capture what someone actually claimed (vs what you
later remember they claimed).

### `batch` — URL list

```bash
receipts batch urls.txt --output-dir reports/
```

Per-video reports + a consolidated `index.json` with verdicts. Use
for systematic review of a creator's catalog or a topic you've been
queueing up.

### `research` *(v0.3)* — topic-driven

```bash
receipts research "intermittent fasting science" --n 7 -o report.md
```

Searches YouTube for the top N videos on a topic, audits each,
synthesizes a cross-video report with:

- **Reading order** — best-evidence videos first; tells you what to
  actually watch.
- **High-evidence claims** — top claims with `evidence_score >= 2/3`
  aggregated across all audited videos. The "show me the receipts"
  cross-cut.
- **Consensus terms** — vocabulary appearing in ≥2 videos. Signals
  canonical concepts in the topic.
- **Failures** — URLs that couldn't be audited (private, captions
  disabled, etc.).

5 minutes vs 3 hours of watching.

## Pluggable vetters

The default `SkeletonVetter` is rule-based: regex for numbers,
sources, testable phrases. It runs offline and is deterministic.
It's a baseline, not the final word.

For real audits, plug in your own `Vetter`:

```python
from receipts import audit
from receipts.audit import AuditReport

class TradingVetter:
    """LLM-backed, web-search-augmented, citation-aware."""
    def vet(self, metadata, transcript, *, domain):
        # ... LLM extracts proper claims ...
        # ... web-search verifies citations ...
        # ... domain-rule scorer ranks evidence ...
        return AuditReport(...)

report = audit(url, vetter=TradingVetter())
```

The Vetter protocol is a single method. See
[recipes.md](recipes.md#recipe-6) for an LLM-backed example.

## Features

- **Refuses to paraphrase.** Verbatim claim extraction.
- **Three-axis evidence scoring.** Number / source / testable.
- **Verdict bucketing.** At-a-glance HIGH/MIXED/LOW/UNSUPPORTED.
- **Three modes.** `audit` / `batch` / `research`.
- **Pluggable Vetter protocol.** Default is offline rule-based; bring
  your own LLM / web-search / domain-specific scorer.
- **Pluggable domain hint.** Optional `--domain` parameter passes
  through to the vetter.
- **MCP server.** `receipts-mcp` exposes `receipts_audit`,
  `receipts_transcribe`, `receipts_research` as native tools to
  Claude Code / Cursor / Cline / Codex.
- **Auto-caption fallback.** YouTube auto-captions have no
  punctuation; receipts falls back to fixed-word chunking so the
  audit still has multiple claim chunks instead of one giant blob.
- **Single dependency.** `yt-dlp`. No API keys required for default mode.

## What receipts solves

- **Pre-watch filter.** 30-second audit before committing 30 minutes
  to a video. Skip 80% of low-evidence content.

- **Cross-video synthesis.** "Of these 5 'best 401k strategies'
  videos, which actually cite studies? Where do they agree?
  Disagree?"

- **AI-agent media literacy primitive.** Today's AI agents can
  summarize a video; none can AUDIT it. Receipts adds the audit
  primitive any agent can call. Agents that adopt it stop
  amplifying low-evidence content.

- **Personal knowledge base.** Archive every video you watch with
  extracted claims + verdict + transcript. Searchable, gradable, and
  honest about what you actually learned vs what you just watched.

- **Receipt-style debunking.** For trading / health / AI influencer
  content specifically, receipts exposes how little hard data is in
  most "guru" videos. Six trading videos audited side-by-side, all
  `LOW_EVIDENCE`. The pattern is unmistakable when you see them
  scored.

## What receipts is NOT

- **Not a summarizer.** Other tools paraphrase; receipts extracts
  verbatim. If you want a summary, ask an LLM directly with the
  transcript.

- **Not a fact-checker.** The default vetter scores claim
  *quality* (does a number exist?), not claim *truth* (is the
  number correct?). For external corroboration, plug in an
  LLM-backed vetter with web search.

- **Not a video downloader.** Captions only — never downloads the
  video itself. ffmpeg not required.

## Composition with `tether`

Receipts' sibling project is [`tether`](https://github.com/axndj1993/tether)
— bidirectional comms for AI agents over Telegram/Slack. Together:

```
Operator (on phone, in Telegram):
    "Quick audit on https://youtu.be/abc"

Claude (with both MCP servers):
    → tether_poll(timeout=30)
    ← [{"text": "Quick audit on...", ...}]
    → tether_send("On it.")                # ack-first
    → receipts_audit(url=..., domain="general")
    ← {verdict: "LOW_EVIDENCE", claims: 8, ...}
    → tether_send("LOW_EVIDENCE. 8 claims, 1 with a number, "
                  "0 with sources. Skim only.")
```

Two MCP servers, ~15 lines of agent logic, fully mobile-driven
video-audit workflow. Both projects are siblings of the same
philosophy: extract the *primitive* you need, ship it tiny, let users
compose.

## Roadmap

- **v0.1** — `audit` mode, CLI, Python lib, default rule-based vetter ✓
- **v0.2** — MCP server ✓
- **v0.3** — `research` mode (topic → top N → synthesize) ✓
- **v0.4** *(planned)* — `compare` mode (compare 2 videos directly,
  highlighting agreements + disagreements)
- **v0.5** *(planned)* — bundled LLM-backed vetter (Anthropic SDK,
  optional dep) for users who want the deeper analysis without
  writing one themselves
- **v1.0** *(planned)* — domain library: `TradingVetter`,
  `HealthVetter`, `TechVetter`, `LegalVetter` — opinionated scoring
  rules for each, opt-in.

The audit primitive is the lasting value; modes and vetters are
extensions.
