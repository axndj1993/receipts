# receipts

> Turn any YouTube video into an evidence audit.

Most "summarize this video" tools paraphrase the speaker. **receipts does
the opposite**: it extracts the speaker's *claims*, scores each one by
evidence quality (does the claim have a number? a source? a testable
mechanism?), and produces a brutally honest Markdown audit.

Useful when you watch a lot of "guru" content (trading, health, AI,
crypto, productivity) and want a 30-second filter for *"is this person
actually saying anything verifiable?"* before adopting their advice.

## Why this exists

- **Most YouTube education is unfalsifiable.** "I made $44K this month"
  with no audited statement, no sample size, no out-of-sample data.
- **Summarizers compound the problem** by paraphrasing the unfalsifiable
  claim into something that *sounds* concise and factual.
- **AI agents need a claim-extraction primitive** for the same reason
  humans do — you can't compare ten videos on a topic in a useful way
  without first stripping each one down to its asserted claims.

`receipts` is that primitive. It refuses to paraphrase. It just extracts
and scores.

## Install

```bash
pip install receipts
```

`yt-dlp` is a dependency and gets installed automatically. No API keys
required for the default rule-based vetter.

## Quickstart

```bash
# Audit one video (writes a Markdown report to stdout):
receipts audit https://youtu.be/0L6Rcgp6j7Y --domain trading -o audit.md

# Just pull the cleaned transcript:
receipts transcribe https://youtu.be/0L6Rcgp6j7Y

# Audit a list of URLs (one per line):
echo "https://youtu.be/0L6Rcgp6j7Y" >  urls.txt
echo "https://youtu.be/abc123"      >> urls.txt
receipts batch urls.txt --domain trading --output-dir reports/
```

The audit report has:
- **Metadata** — title, channel, upload date, duration, views.
- **Verdict** — `HIGH_EVIDENCE` / `MIXED` / `LOW_EVIDENCE` / `UNSUPPORTED`.
- **Claims table** — every claim-like sentence + score on three axes:
  - has number? (5%, 1.5x, $1500, n=42, ...)
  - has source? (study, paper, n=N, OOS, sharpe, win-rate, ...)
  - testable? (conditional / declarative — "when X, do Y")
- **Vetter notes** — caveats and recommendations.
- **Full transcript** — for citation.

## Python usage

```python
from receipts import audit

report = audit("https://youtu.be/0L6Rcgp6j7Y", domain="trading")
print(report.verdict)            # 'MIXED'
for c in report.claims:
    print(c.evidence_score, c.text[:80])
print(report.to_markdown())
```

## Pluggable vetters

The default `SkeletonVetter` is rule-based and runs offline. For deeper
audits, plug in a domain-specialized vetter (LLM-backed, web-search-
augmented, citation-aware):

```python
from receipts import audit, fetch_video, clean_vtt

class TradingVetter:
    """Knows what real backtest evidence looks like."""
    def vet(self, metadata, transcript, *, domain):
        # ... LLM call, web search, citation lookup ...
        return AuditReport(...)

report = audit(url, vetter=TradingVetter())
```

Vetters implement the `Vetter` protocol — see [docs/api-reference.md].

## Use as a Claude Code Skill

Drop a Skill definition that wraps `receipts audit` so Claude can do
"watch + audit" loops on demand:

```markdown
---
name: receipts-audit
description: Use when the user shares a YouTube URL and asks "what's in this?" or "is this any good?" Audits the video's claims for evidence quality.
---

# Skill rules
1. Call `receipts audit URL --domain <inferred> -o /tmp/audit_<id>.md`.
2. Read the audit report, surface the verdict + 3-5 highest/lowest
   scoring claims back to the user.
3. Keep the report on disk for follow-up.
```

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

- [Installation](docs/installation.md)
- [Quickstart](docs/quickstart.md)
- [API reference](docs/api-reference.md)
- [CLI reference](docs/cli-reference.md)
- [Recipes](docs/recipes.md)
- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)

## License

MIT.
