# Research mode

> `receipts research "topic" --n 5`

`receipts` v0.3 introduces a **research mode**: feed it a topic, it
searches YouTube for the top N results, audits each, and synthesizes a
cross-video report — reading order, consensus terms, high-evidence
claims aggregated across the corpus.

## Why this exists

Auditing one video at a time is useful, but the more interesting
question is usually:

> *"What does YouTube collectively say about X — and which videos
> actually have evidence vs which are vibes?"*

Doing that by hand: find 5-10 videos, watch them all, take notes,
compare. ~3 hours.

Doing it with `receipts research`: 5 minutes, structured output,
reading-order recommendation, terms that recur across videos, the
strongest claims pulled out automatically.

## Usage

### CLI

```bash
receipts research "intermittent fasting" --n 7 -o fasting.md
receipts research "TSMOM strategies" --n 5 \
    --domain trading \
    --output-dir reports/tsmom/
```

`--output-dir` (optional): also writes per-video Markdown reports +
`index.json` so the cross-video report links back to the individual
audits.

### Python

```python
from receipts import research

report = research(
    "intermittent fasting science",
    n=7,
    domain="health",
)

print(report.verdict_summary())
for r in report.reading_order():
    print(f"{r.verdict:15} {r.metadata.title}")

# Markdown render of the cross-video synthesis
print(report.to_markdown())
```

### MCP

```
receipts_research(topic="best 401k strategies", n=5, domain="finance")
```

Returns JSON with reading order, high-evidence claims, consensus terms,
and any fetch failures. Drop into Claude Code / Cursor / Cline /
Codex via `receipts-mcp` (see [mcp.md](mcp.md)).

## Output sections

A `ResearchReport.to_markdown()` produces:

1. **Header** — topic, domain, audited count, failure count.
2. **Reading order** — table of all audited videos, sorted by verdict
   bucket (HIGH_EVIDENCE first), then by claim count. Tells you which
   to actually watch.
3. **High-evidence claims** — for every video that scored
   `HIGH_EVIDENCE`, the top-5 claims with `evidence_score >= 2/3`.
   This is the "show me the receipts" cross-cut: the strongest
   moments in the entire corpus.
4. **Consensus terms** — vocabulary appearing in ≥2 of the audited
   videos (lowercase, stop-words filtered, length ≥ 4). Useful for
   spotting canonical concepts in a topic — terms a writeup of the
   topic should probably define.
5. **Fetch failures** — any URLs `yt-dlp` couldn't process (private,
   captions disabled, etc).

## How it works under the hood

```
topic
  │
  ▼
yt-dlp --flat-playlist --print %(id)s ytsearchN:topic
  │
  ▼
[url1, url2, ..., urlN]
  │
  ▼  (per-url, in sequence)
audit(url, domain=...)  ── failures collected separately
  │
  ▼
[AuditReport, AuditReport, ...]
  │
  ▼
synthesize:
  - reading_order = sorted by verdict bucket then claim count
  - high_evidence_audits = filter verdict=HIGH_EVIDENCE
  - consensus_terms = doc-frequency >= 2 across transcripts
  │
  ▼
ResearchReport
```

## Knobs

| Arg                       | Default     | Meaning |
|---------------------------|-------------|---------|
| `topic`                   | required    | Free-form topic string. Specific is better. |
| `n`                       | `5`         | Top N YouTube results to audit. 3-7 typical; >10 gets noisy. |
| `domain`                  | `"general"` | Hint for the per-video vetter. |
| `vetter`                  | `None`      | Optional `Vetter` to override the default `SkeletonVetter`. |
| `max_consensus_terms`     | `30`        | Cap the consensus-terms table. |

## Tips for picking topics

- **Specific > generic.** "TSMOM time-series momentum strategies" beats
  "trading"; "intermittent fasting circadian rhythm" beats "fasting".
- **Avoid trademarked names** — they pull in shilling videos. "iPhone"
  → product reviews. "iPhone supply chain analysis" → real research.
- **Use the channel context too.** YouTube's search ranks creator
  authority; if the topic intersects 1-2 well-known niches, the top
  results will be those creators' videos. That's good if those
  creators are the experts; bad if they're just popular.

## Limits

- **Sequential audits.** Each video's audit is one yt-dlp call (~3-10s)
  + one cleanup pass. Five videos = ~30-60s. Could parallelize, but
  YouTube rate-limits us if we do — sequential is safer.
- **No cross-claim deduplication.** If three videos make the same
  claim ("eat clean for 3 months → metabolic boost"), you'll see all
  three in the high-evidence section. Future enhancement: cluster
  similar claims via an LLM.
- **No external fact-checking.** The skeleton vetter scores *claim
  quality*, not *claim truth*. To add external corroboration, plug
  in an LLM-backed Vetter — see [recipes.md](recipes.md#recipe-6).

## Example session

```bash
$ receipts research "intermittent fasting science" --n 5 --domain health
# Research: intermittent fasting science

**Domain:** health
**Videos audited:** 5

## Reading order (best evidence first)

| Rank | Verdict        | Claims | Title                                | URL |
|------|----------------|--------|--------------------------------------|-----|
| 1    | MIXED          | 18     | Time-restricted eating: 5-yr study   | ... |
| 2    | LOW_EVIDENCE   | 12     | I Tried Fasting for 30 Days          | ... |
| 3    | LOW_EVIDENCE   | 8      | Fasting Mistakes That'll Ruin You    | ... |
| 4    | UNSUPPORTED    | 4      | Why You Should NEVER Fast            | ... |
| 5    | UNSUPPORTED    | 2      | The Truth About Fasting              | ... |

[... high-evidence claims, consensus terms, ...]
```

In ~30s you've gone from "I want to learn about fasting" to "watch
video #1, skim #2, ignore #3-5; the canonical concepts in the topic
are X / Y / Z."
