# Recipes

## Recipe 1 — "Should I watch this?" filter for new videos

Audit before you watch. If `LOW_EVIDENCE` or `UNSUPPORTED`, skip.

```bash
#!/bin/bash
# usage: should-i-watch <YouTube URL>
URL="$1"
verdict=$(receipts audit "$URL" 2>/dev/null | grep "^\\*\\*Verdict:" | cut -d'`' -f2)
case "$verdict" in
  HIGH_EVIDENCE|MIXED) echo "Worth watching. Verdict: $verdict" ;;
  LOW_EVIDENCE)        echo "Skim only. Verdict: $verdict" ;;
  UNSUPPORTED)         echo "Skip. Verdict: $verdict" ;;
  *)                   echo "Couldn't audit." ;;
esac
```

## Recipe 2 — Bulk-audit a YouTube playlist

```bash
yt-dlp --flat-playlist --print "https://youtu.be/%(id)s" \
       "https://www.youtube.com/playlist?list=PL..." > urls.txt
receipts batch urls.txt --output-dir playlist_reports/

# Sort by verdict
jq -r 'sort_by(.verdict) | .[] | "\(.verdict)\t\(.title)"' \
  playlist_reports/index.json
```

## Recipe 3 — Compare 5 videos on the same topic

```bash
cat <<EOF > urls.txt
https://youtu.be/aaa
https://youtu.be/bbb
https://youtu.be/ccc
https://youtu.be/ddd
https://youtu.be/eee
EOF

receipts batch urls.txt --domain trading --output-dir cmp/

# Build a CSV of verdicts to spot which ones cite real evidence
jq -r '.[] | [.verdict, .n_claims, .channel, .title] | @csv' \
  cmp/index.json
```

## Recipe 4 — Telegram alert for every red-flag claim found

Pair receipts with [pager](https://github.com/<org>/pager) (or any
notifier) to get pinged when an audit produces a `HIGH_EVIDENCE` claim
in a "trading guru" video — i.e. when one of these gurus actually
shows their math.

```python
from receipts import audit
from pager import Pager

p = Pager()
URLS = ["https://youtu.be/...", "https://youtu.be/..."]

for url in URLS:
    report = audit(url, domain="trading")
    high = [c for c in report.claims if c.evidence_score >= 2]
    if high:
        p.send(f"*{report.metadata.title}* has {len(high)} high-evidence "
               f"claims. Verdict: `{report.verdict}`. Worth a watch.\n{url}")
```

## Recipe 5 — Personal video knowledge base

Run receipts over every video you watch this week; commit the audits to a
git repo. Use the `index.json` as a searchable catalog.

```bash
mkdir -p ~/video-vault
cd ~/video-vault
git init

# Append today's URL to a list, audit overnight via cron
echo "$URL" >> $(date +%Y-%m).urls
receipts batch $(date +%Y-%m).urls --output-dir reports/$(date +%Y-%m)/
git add . && git commit -m "weekly audit"
```

Three months later you can grep:

```bash
grep -l "MIXED" reports/*/*.md         # mixed-evidence audits this quarter
jq '.[] | select(.verdict=="HIGH_EVIDENCE")' reports/*/index.json
```

## Recipe 6 — LLM-backed vetter (Anthropic)

For real claim extraction (not regex), plug in an LLM:

```python
import anthropic
from receipts import audit
from receipts.audit import AuditReport, Claim

class AnthropicVetter:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def vet(self, metadata, transcript, *, domain):
        prompt = f"""You are an evidence auditor. Extract every CLAIM the
speaker makes from this {domain} video transcript. For each claim, mark:
- has_number: contains a quantitative figure?
- has_source: cites a study/paper/dataset?
- is_testable: stated as a rule or condition?

Reply as JSON: {{"claims": [{{"text": "...", "has_number": true, ...}}]}}

Transcript:
{transcript.text[:30000]}
"""
        msg = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        # ... parse, build claims, compute verdict ...
        return AuditReport(...)

report = audit(url, vetter=AnthropicVetter(), domain="trading")
```

## Recipe 7 — Cite a claim with a timecode

`Transcript.cues` has `(start_seconds, line_text)` tuples. To find which
cue a claim came from, fuzzy-match the claim text against the cue
texts:

```python
from difflib import SequenceMatcher

def find_timecode(transcript, claim_text):
    best_score = 0.0
    best_start = 0.0
    for start, line in transcript.cues:
        score = SequenceMatcher(None, claim_text[:80], line[:80]).ratio()
        if score > best_score:
            best_score, best_start = score, start
    return best_start

# Usage:
for c in report.claims[:5]:
    t = find_timecode(report.transcript, c.text)
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    timecode = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    print(f"[{timecode}] {c.text[:80]}...")
```
