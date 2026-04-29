# Quickstart — five minutes to your first audit

## 1. Audit one video

```bash
receipts audit https://youtu.be/0L6Rcgp6j7Y --domain trading -o audit.md
```

Open `audit.md`. You'll see something like:

```markdown
# Audit: Four Price Action Secrets ...

**Channel:** TradingLab
**Uploaded:** 20211022
**Duration:** 8m 10s
**Views:** 2,209,821
**Verdict:** `LOW_EVIDENCE` (domain: trading)

## Summary
[first 800 chars of transcript]

## Claims (24)
| # | Claim | Number? | Source? | Testable? | Score |
|---|-------|---------|---------|-----------|-------|
| 1 | ...                                | N | N | Y | 1/3 |
| 2 | ...some sentence with 50%          | Y | N | Y | 2/3 |
...

## Vetter notes
[caveats]

## Transcript
[full cleaned text]
```

The verdict at the top is the headline. Drill into the claims table for
specifics — sort by Score column to find the strongest / weakest claims.

## 2. Just the transcript

```bash
receipts transcribe https://youtu.be/0L6Rcgp6j7Y
# clean lower-case transcript dumped to stdout
```

Or as JSON for programmatic use:

```bash
receipts transcribe https://youtu.be/0L6Rcgp6j7Y --json
```

Returns metadata + per-cue timestamps so you can quote with timecodes.

## 3. Audit a batch

`urls.txt`:

```
# trading gurus
https://youtu.be/0L6Rcgp6j7Y
https://youtu.be/abc123
https://youtu.be/xyz789
```

```bash
receipts batch urls.txt --domain trading --output-dir reports/
```

Produces:

```
reports/
├── 0L6Rcgp6j7Y.md       # one Markdown report per video
├── abc123.md
├── xyz789.md
└── index.json           # consolidated summary: per-video verdict + report path
```

## 4. Python — the same flow programmatically

```python
from receipts import audit

report = audit("https://youtu.be/0L6Rcgp6j7Y", domain="trading")
print(report.metadata.title)
print(report.verdict)
high = [c for c in report.claims if c.evidence_score >= 2]
print(f"{len(high)} high-evidence claims")
print(report.to_markdown())
```

## 5. Custom vetter — drop-in your own scoring

```python
from receipts import audit, AuditReport

class MyDomainVetter:
    def vet(self, metadata, transcript, *, domain):
        # ... your LLM call, regex rules, web-search lookups ...
        return AuditReport(
            metadata=metadata,
            transcript=transcript,
            claims=[...],
            verdict="MIXED",
            summary="...",
            notes="my custom analysis",
        )

report = audit("https://youtu.be/...", vetter=MyDomainVetter())
```

The `Vetter` protocol is just a single method. See
[architecture](architecture.md) for the design rationale.

## Useful next reads

- [API reference](api-reference.md) — every Python class/method
- [CLI reference](cli-reference.md) — every subcommand
- [Recipes](recipes.md) — common patterns
- [Architecture](architecture.md) — pipeline + extension points
- [Troubleshooting](troubleshooting.md) — when fetch fails, etc.
