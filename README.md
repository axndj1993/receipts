# receipts

> Show me the receipts. Turn any YouTube video into an evidence audit.

You bookmark 50 videos a month to "learn from later" — and never
watch them. You consider a $200 paid course but don't know if it's
any good. Someone shares a link with "this changed how I think
about X" — and now you owe them a polite watch. You're researching a
topic and somehow it's 11pm and you've watched 7 vague videos in a
row.

The thing in common: you can't tell from the thumbnail / title /
runtime whether a video has *receipts* — actual numbers, sources,
testable claims — versus 30 minutes of confidence wearing the
costume of expertise.

`receipts` is the filter. Feed it a URL or a topic; it extracts
every claim the speaker makes, scores each on three axes (has a
*number*? a *source*? a *testable rule*?), and produces a Markdown
audit ranked best-evidence-first.

```
$ receipts audit https://youtu.be/<id> --domain trading

# Audit: I made $44K This Month with One Setup

**Verdict:** `LOW_EVIDENCE` (1 claim with a number, 0 with sources)

| # | Claim                                  | Number? | Source? | Testable? | Score |
|---|----------------------------------------|---------|---------|-----------|-------|
| 1 | "I made $44k this month"               | Y       | N       | N         | 1/3   |
| 2 | "70% win rate on this setup"           | Y       | N       | Y         | 2/3   |
| 3 | "the market always reverts"            | N       | N       | Y         | 1/3   |
...
```

Skip the video. Five seconds saved you a 27-minute commitment.

---

## What people use it for

**Skim your watch-later queue.** Audit 50 queued URLs, sort by
verdict, watch the top 5. Skip the rest.

**Pre-screen paid courses.** Audit the free preview before spending
$200 on Udemy / Coursera / Skillshare.

**Topic research, ranked by evidence.** Tell receipts to find the
top 7 YouTube videos on *intermittent fasting science* — it audits
each, gives you a reading-order best-evidence-first, surfaces the
high-evidence claims aggregated across the corpus, and shows the
canonical vocabulary the topic uses. ~5 minutes vs ~3 hours of
trial-and-error watching.

**Spot grift in finance / health / AI YouTube.** Pipe a creator's
last 30 videos through `receipts batch`; aggregate verdict
distribution = trust calibrated by data, not subscriber count.

**Build a permanent learning archive.** Every video you watch goes
through receipts; commit the audits to a private git repo. Six
months later you can grep your archive — *every HIGH_EVIDENCE video
on machine learning I saved this year* — a curated, evidence-graded
learning corpus, not a YouTube history list.

**Track topic evolution.** Re-research the same topic every 3
months; verdicts shifting from MIXED to HIGH_EVIDENCE = field
maturing. Useful for fast-moving fields (AI, biotech, crypto).

Full per-persona examples in [**docs/use-cases.md**](docs/use-cases.md)
(student, developer, AI engineer, trader, researcher, educator,
investor, journalist, health, generic learner — 30+ patterns).

> *Sibling project:* [`tether`](https://github.com/axndj1993/tether) —
> bidirectional Telegram/Slack comms for AI agents. Compose the two:
> share a YouTube URL via Telegram → agent audits with receipts →
> result back via tether. Mobile-driven, ~15 lines of agent logic.

---

## What problem this solves

YouTube has roughly **500 hours uploaded per minute**. A meaningful
slice is "expert" content — finance, health, AI, productivity,
legal, political. Most of it is **unfalsifiable confidence wearing
the costume of expertise**: no quantified evidence, no sources, no
sample sizes, no out-of-sample data, no conflicts-of-interest
disclosed.

Two existing approaches both fail at scale:

- **Watch the whole video.** Doesn't scale. You can't evaluate 50
  videos a week this way, and most aren't worth a 30-minute
  commitment in the first place.

- **Use a summarizer / NotebookLM-style tool.** These *paraphrase*
  the unfalsifiable claim into something that *sounds* concrete —
  making the bad content *more* believable, not less. The summary
  smooths over the speaker's missing receipts.

`receipts` does the opposite. It refuses to paraphrase. It just
extracts the claims verbatim and scores them.

Full motivation, problem framing, features, roadmap in
[**docs/why.md**](docs/why.md).

---

## Three modes

- **`audit URL`** — score one video's claims (the v0.1 baseline).
- **`research "topic" --n 7`** — search YouTube for the top N
  videos on a topic, audit each, synthesize cross-video reading
  order + consensus terms + aggregated high-evidence claims.
  *(v0.3)*
- **MCP server** — `receipts-mcp` exposes audit + transcribe +
  research as native tools to Claude Code / Cursor / Cline / Codex.
  *(v0.2)*

## Install

```bash
pip install receipts            # core
pip install 'receipts[mcp]'      # + MCP server
```

`yt-dlp` is a dependency and gets installed automatically. No API
keys required for the default rule-based vetter.

## 60-second start

```bash
# Audit one video (writes a Markdown report to stdout):
receipts audit https://youtu.be/<id> -o audit.md

# Research a topic — best-evidence-first reading order:
receipts research "transformers attention mechanism" --n 7 -o syllabus.md

# Audit a batch of URLs, get an index.json with verdicts:
receipts batch urls.txt --output-dir reports/
```

## Use it from Claude Code (or Cursor / Cline / Codex / Continue / Zed)

One-liner to wire the MCP server into your AI host's config:

```bash
cd <your-project>
receipts install claude-code            # writes .mcp.json (project root)
# or: receipts install cursor / cline / codex / continue / zed
```

Restart the host. In Claude Code, `/mcp` should now list `receipts`
with the three tools (`receipts_audit`, `receipts_transcribe`,
`receipts_research`). The agent can call them directly when you
share a YouTube URL or ask for topic research.

Existing servers in your config (e.g. `tether`) are preserved — the
installer only writes/overwrites the `receipts` entry. Full
per-host paths in [docs/cli-reference.md](docs/cli-reference.md#receipts-install-host-options).

## Python

```python
from receipts import audit, research

# Single video
r = audit("https://youtu.be/<id>")
print(r.verdict)                          # 'MIXED'
high = [c for c in r.claims if c.evidence_score >= 2]
print(f"{len(high)} high-evidence claims")

# Topic research
res = research("LLM agent design patterns", n=5)
for r in res.reading_order():
    print(f"{r.verdict:15} {r.metadata.title}")
```

## Pluggable vetters

The default `SkeletonVetter` is rule-based and runs offline. For
deeper audits, plug in a domain-specialized vetter (LLM-backed,
web-search-augmented, citation-aware):

```python
from receipts import audit, AuditReport

class HealthVetter:
    """Cross-references claims against PubMed + Cochrane Library."""
    def vet(self, metadata, transcript, *, domain):
        # extract claims via LLM
        # for each quantitative claim, search PubMed
        return AuditReport(...)

report = audit(url, vetter=HealthVetter())
```

Vetters implement the `Vetter` protocol — see
[docs/api-reference.md](docs/api-reference.md).

## What receipts is NOT

- **Not a summarizer.** Other tools paraphrase; receipts extracts
  verbatim. If you want a summary, ask an LLM directly with the
  transcript.

- **Not a fact-checker.** The default vetter scores *evidence
  quality* (does a number exist?), not *truth* (is the number
  correct?). For external corroboration, plug in an LLM-backed
  vetter with web search.

- **Not a video downloader.** Captions only — never downloads the
  video. ffmpeg not required.

## Documentation

| Page                                    | What's in it |
|-----------------------------------------|---|
| [Why receipts](docs/why.md)             | Full motivation + roadmap |
| [Use cases](docs/use-cases.md)          | 30+ patterns by persona (student / developer / AI engineer / trader / researcher / educator / etc.) |
| [Installation](docs/installation.md)    | Install + verify |
| [Quickstart](docs/quickstart.md)        | 5-minute walkthrough |
| [API reference](docs/api-reference.md)  | Every Python class/method |
| [CLI reference](docs/cli-reference.md)  | Every subcommand/flag |
| [Integrations](docs/integrations.md)    | Step-by-step for Claude Code, Cursor, Cline, Codex, Continue.dev, Zed, Anthropic SDK, plain Python, CI |
| [MCP server](docs/mcp.md)               | Drop receipts into MCP-aware clients as native tools |
| [Research mode](docs/research.md)       | Topic → top N → synthesize |
| [Recipes](docs/recipes.md)              | Cookbook: playlist audit, knowledge base, LLM-backed vetter |
| [Architecture](docs/architecture.md)    | Pipeline, Vetter protocol, extension points |
| [Troubleshooting](docs/troubleshooting.md) | yt-dlp errors, missing captions, false-positive verdicts |

## License

MIT.
