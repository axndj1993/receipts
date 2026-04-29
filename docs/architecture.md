# Architecture

receipts is a thin pipeline:

```
┌──────────┐    ┌───────────────┐    ┌──────────────┐    ┌──────────────┐
│ YouTube  │ -> │ receipts.fetcher│ -> │receipts.transcript -> │ receipts.audit │
│  URL     │    │   (yt-dlp)    │    │  (clean VTT) │    │   (Vetter)   │
└──────────┘    └───────────────┘    └──────────────┘    └──────┬───────┘
                                                                │
                                                            ┌───▼───────┐
                                                            │ AuditReport│
                                                            │ -> Markdown│
                                                            └───────────┘
```

## Stages

### `receipts.fetcher`

Wraps `yt-dlp --skip-download --write-auto-sub --write-info-json`.
Returns `(VideoMetadata, raw_vtt_text)`. Does not retain files unless
`keep_files=True`.

**Why yt-dlp?** It handles every YouTube edge case (age-gated, region-
locked, captions-disabled, multi-language tracks) and falls back
gracefully. Building this ourselves on the YouTube Data API would lock
us into Google's quota and key management.

**Limitations:**
- yt-dlp can be brittle when YouTube changes their player. If a fetch
  fails with "no JS runtime", install a JavaScript runtime (deno, node)
  per the warning's URL.
- Auto-generated captions only exist when YouTube has decoded speech.
  Music-only / low-volume / heavily-accented videos may have no usable
  caption track.

### `receipts.transcript`

Parses the VTT into `Transcript(text, cues)`:
- drops headers (`WEBVTT`, `Kind:`, `Language:`)
- drops timing lines (`00:00:01.000 --> 00:00:03.000`)
- strips inline tags (`<00:00:01.000>`, `<c>...</c>`)
- dedups contiguous duplicate lines (auto-captions repeat each phrase
  several times across cues)

The `cues` list preserves per-cue start timestamps so callers can quote
with timecodes. The `text` field is the flat, deduped, lowercase blob.

### `receipts.audit`

The `Vetter` protocol:

```python
class Vetter(Protocol):
    def vet(self, metadata, transcript, *, domain) -> AuditReport: ...
```

Anyone can implement this. The default `SkeletonVetter` is rule-based:

1. Split the transcript into sentence-ish chunks. If the transcript has
   real punctuation, split on `.!?` followed by a capital letter.
   Otherwise (auto-captions = no punctuation), fall back to
   fixed-word chunks (default 40 words).
2. For each chunk, compute three boolean flags:
   - `has_number` — regex for `5%`, `1.5x`, `$1,500`, `n=42`
   - `has_source` — regex for "study", "paper", "OOS", "Sharpe",
     "win-rate", etc.
   - `is_testable` — regex for "when", "if", "rule", "setup", "trigger"
3. Include the chunk as a `Claim` if at least one flag is true.
4. Verdict = bucketed average `evidence_score` across claims.

This is intentionally crude — it's a baseline, not the final word. Real
audits should plug in an LLM-backed vetter that does proper claim
extraction (NER + normalization) and cross-references claims against
external evidence (papers, market data, audited statements, etc.).

### `AuditReport.to_markdown()`

Pure rendering. Reads the populated dataclass, emits Markdown sections:
metadata, verdict, summary, claims table, vetter notes, full transcript.

## Extension points

### Add a new vetter

```python
from receipts import audit
from receipts.audit import AuditReport, Claim

class TradingVetter:
    def __init__(self, llm_client):
        self.llm = llm_client

    def vet(self, metadata, transcript, *, domain):
        # 1. LLM call: extract claims with timestamps.
        # 2. For each claim with quantitative content, search public
        #    backtest databases / Quantocracy / etc.
        # 3. Score: cited paper -> +1; cited audited statement -> +2;
        #    "trust me bro" -> 0.
        # 4. Aggregate to verdict.
        return AuditReport(...)

report = audit(url, vetter=TradingVetter(llm_client=...))
```

### Add a new domain hint

The `domain` parameter is a free-form string passed through to the
vetter. The `SkeletonVetter` ignores it; specialized vetters can branch:

```python
def vet(self, metadata, transcript, *, domain):
    if domain == "trading":
        # apply trading-specific rules
    elif domain == "health":
        # apply health-specific rules
    else:
        # generic
```

### Replace the fetcher

Implement your own `fetch_video`-shaped function (returns
`(VideoMetadata, raw_vtt)`) and call `clean_vtt` + your vetter directly:

```python
from receipts.transcript import clean_vtt
from receipts.audit import SkeletonVetter

meta, raw_vtt = my_custom_fetch(url)         # e.g. local cache, S3, etc.
transcript = clean_vtt(raw_vtt)
report = SkeletonVetter().vet(meta, transcript, domain="general")
```

## Where receipts does NOT go

- **No video download.** Captions only.
- **No paraphrasing in the report.** The "summary" is literally the
  first 800 chars of the transcript. The point of receipts is to NOT
  smooth over what the speaker actually said.
- **No automatic web-search / fact-checking.** That belongs in a
  domain-specialized vetter that the user plugs in.
- **No per-claim timecode lookup.** Doable via `Transcript.cues` but
  not in v0.1 — would need a fuzzy text-to-cue matcher.
