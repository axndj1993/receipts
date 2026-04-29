# receipts

> Turn any YouTube video into an evidence audit.

Most "summarize this video" tools paraphrase the speaker. **receipts does
the opposite**: it extracts the speaker's *claims*, scores each one by
evidence quality (does the claim have a number? a source? a testable
mechanism?), and produces a brutally honest Markdown audit.

Useful when you (or your AI agent) want a 30-second filter for
*"is this person actually saying anything verifiable?"* before
investing 30 minutes watching — across any topic where YouTube is the
default learning channel: nutrition, AI/ML, productivity, science
explainers, legal commentary, history, finance, software tutorials.

## Why this exists

> Today's meta-challenge: YouTube has ~500 hours uploaded *per minute*.
> A meaningful slice is "expert" content — finance, health, AI,
> productivity, legal. Most of it is unfalsifiable confidence wearing
> the costume of expertise. Existing summarizers paraphrase the bad
> claim into something that *sounds* concrete; AI agents that watch
> videos for users do the same. There's no fast filter for *"is this
> person actually showing the receipts?"*

`receipts` is the filter:

- **Most YouTube education is unfalsifiable.** "I made $44K this
  month" with no audited statement, no sample size, no out-of-sample
  data.
- **Summarizers compound the problem** by paraphrasing the
  unfalsifiable claim into something that *sounds* concise and factual.
- **AI agents need a claim-extraction primitive** for the same reason
  humans do — you can't compare ten videos on a topic in a useful way
  without first stripping each one down to its asserted claims.

`receipts` is that primitive. It refuses to paraphrase. It just
extracts and scores.

Full motivation, problem framing, features, and roadmap in
[**docs/why.md**](docs/why.md).

> *Sibling project:* [`tether`](https://github.com/axndj1993/tether) —
> bidirectional comms for AI agents over Telegram/Slack. Compose the
> two for mobile-driven workflows: operator shares a YouTube URL via
> Telegram → agent audits with receipts → result back via tether.

**Three modes:**
- **`audit`** — score one video's claims (the v0.1 baseline)
- **`research`** *(v0.3)* — search YouTube for the top N videos on a
  topic, audit each, synthesize a cross-video report (reading order,
  consensus terms, high-evidence claims aggregated across the corpus)
- **MCP server** *(v0.2)* — `receipts-mcp` exposes audit + transcribe +
  research as native tools to Claude Code / Cursor / Cline / Codex

## Install

```bash
pip install receipts
```

`yt-dlp` is a dependency and gets installed automatically. No API keys
required for the default rule-based vetter.

## Quickstart

### 1. Research a topic — best-evidence-first reading order

You're curious about *time-restricted eating* and want to learn
without watching ten videos. One command:

```bash
receipts research "time-restricted eating science" --n 5 -o trf.md
```

`trf.md` ranks the top 5 YouTube results best-evidence-first, surfaces
the high-evidence claims aggregated across the corpus, and shows the
consensus vocabulary the topic uses. ~30 seconds vs ~3 hours of
watching.

```markdown
# Research: time-restricted eating science

| Rank | Verdict        | Claims | Title                                | URL |
|------|----------------|--------|--------------------------------------|-----|
| 1    | MIXED          | 18     | A 5-yr randomized trial of TRE       | ... |
| 2    | LOW_EVIDENCE   | 12     | I Tried Fasting for 30 Days          | ... |
| 3    | LOW_EVIDENCE   | 8      | Fasting Mistakes That'll Ruin You    | ... |
| 4    | UNSUPPORTED    | 4      | Why You Should NEVER Fast            | ... |
| 5    | UNSUPPORTED    | 2      | The Truth About Fasting              | ... |

## High-evidence claims across the topic
[verbatim quotes from video #1, with evidence_score >= 2/3]

## Consensus terms (across multiple videos)
| Term              | Videos |
|-------------------|--------|
| circadian         | 4      |
| insulin           | 3      |
| autophagy         | 3      |
| ...
```

You watch video #1 (the only `MIXED` evidence one), skim #2-3, ignore
#4-5.

### 2. Audit one video — quick verdict before committing 30 min

```bash
receipts audit https://www.youtube.com/watch?v=<id> -o audit.md
```

Returns the same shape as one entry of the research report:
verdict + claims table + vetter notes + transcript.

### 3. Just the transcript — no audit, no paraphrase

```bash
receipts transcribe https://www.youtube.com/watch?v=<id>
```

Use it for citation, search, or feeding into a different downstream
LLM step.

## What's in the audit report

- **Metadata** — title, channel, upload date, duration, views.
- **Verdict** — `HIGH_EVIDENCE` / `MIXED` / `LOW_EVIDENCE` / `UNSUPPORTED`.
- **Claims table** — every claim-like sentence + score on three axes:
  - has number? (5%, 1.5x, n=42, $1500, ...)
  - has source? (study, paper, OOS, win-rate, audited statement, ...)
  - testable? (declarative + conditional — "when X, do Y")
- **Vetter notes** — caveats and recommendations.
- **Full transcript** — verbatim, for citation.

## Python usage

```python
from receipts import audit, research

# Single-video audit
r = audit("https://youtu.be/<id>")
print(r.verdict)                    # 'MIXED'
high = [c for c in r.claims if c.evidence_score >= 2]
print(f"{len(high)} high-evidence claims")

# Topic research — top N → audit each → synthesize
res = research("transformers attention mechanism", n=5)
for r in res.reading_order():
    print(f"{r.verdict:15} {r.metadata.title}")
print(res.to_markdown())
```

## Pluggable vetters

The default `SkeletonVetter` is rule-based and runs offline. For deeper
audits, plug in a domain-specialized vetter (LLM-backed, web-search-
augmented, citation-aware):

```python
from receipts import audit, AuditReport

class HealthVetter:
    """Cross-references claims against PubMed + Cochrane Library."""
    def vet(self, metadata, transcript, *, domain):
        # extract claims via LLM
        # for each quantitative claim, search PubMed
        # tag claims by 'cited / citable / unsupported'
        return AuditReport(...)

report = audit(url, vetter=HealthVetter())
```

Vetters implement the `Vetter` protocol — see [docs/api-reference.md].

Vetters implement the `Vetter` protocol — see [docs/api-reference.md].

## Use as a Claude Code Skill

Drop a Skill definition that wraps `receipts` so Claude can do
"watch + audit" loops AND topic research on demand:

```markdown
---
name: receipts-audit
description: Use when the user (a) shares a YouTube URL and asks "what's in this?" / "is this any good?", or (b) asks to research a topic ("find the best videos on X"). Audits claims for evidence quality and ranks results best-evidence-first.
---

# Skill rules
1. **Single URL** → `receipts audit URL -o /tmp/audit_<id>.md`.
   Surface the verdict + 3-5 highest/lowest scoring claims to the user.
2. **Topic research** → `receipts research "TOPIC" --n 5 --output-dir /tmp/r/`.
   Surface the reading order + the high-evidence claims aggregated
   across the corpus.
3. Keep reports on disk for follow-up questions.
```

Or skip the Skill — install [`receipts-mcp`](docs/mcp.md) and Claude
Code (or Cursor/Cline/Codex) gets `receipts_audit` /
`receipts_transcribe` / `receipts_research` as native tools with no
glue code.

## Limits + non-goals

- **receipts doesn't watch the video** — it reads the auto-generated
  captions YouTube produces. Visual-only content (charts, code on
  screen) is invisible to it.
- **receipts doesn't paraphrase.** A "summary" in receipts's report is the
  literal first 800 characters of the transcript, not a rewrite.
- **receipts doesn't fact-check the world** — the default vetter scores
  the *quality* of evidence (does a number exist?), not the *truth* of
  the claim. Plug in an LLM-backed vetter with web search if you want
  external corroboration.
- **No videos without captions.** If YouTube has no auto-caption track
  in the requested language, receipts errors out with a clear message.

## Documentation

- [Why receipts exists](docs/why.md) — full motivation + roadmap
- [Installation](docs/installation.md)
- [Quickstart](docs/quickstart.md)
- [API reference](docs/api-reference.md)
- [CLI reference](docs/cli-reference.md)
- [MCP server](docs/mcp.md) — drop into Claude Code / Cursor / etc
- [Research mode](docs/research.md) — topic → top N → synthesize
- [Recipes](docs/recipes.md)
- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)

## License

MIT.
