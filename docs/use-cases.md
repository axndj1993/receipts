# Use cases

Anywhere you'd otherwise watch 5-10 videos to learn or evaluate a
topic, `receipts` compresses the decision-making to ~30 seconds + 1
actual watch. Ten patterns where this pays off.

## 1. Skim my watch-later queue

You bookmark 50+ videos a month and never watch them. Audit the
queue, sort by evidence quality, watch only the top few:

```bash
# urls.txt — your watch-later, one URL per line
receipts batch urls.txt --output-dir queue_reports/

# Sort by verdict
jq -r '.[] | "\(.verdict)\t\(.title)"' queue_reports/index.json | sort
```

Watch the `HIGH_EVIDENCE` and `MIXED` rows. Mark the rest deleted.

## 2. Pre-watch filter for paid courses

Considering a $200 Udemy / Skillshare / Coursera course? Most have a
free preview / sample lesson. Audit those:

```bash
receipts audit "https://youtu.be/<preview-video-id>" --domain education
```

If the preview is `LOW_EVIDENCE` or `UNSUPPORTED`, the paid course
probably isn't either — instructors don't usually save their best
material for the paywall.

## 3. "What's the consensus on X?"

You're researching a topic for a decision. You'd normally read 10
articles or watch 8 videos. Replace with:

```bash
receipts research "intermittent fasting circadian science" --n 10
```

The synthesis surfaces:
- Reading order — best-evidence-first
- Consensus terms — vocabulary that recurs across multiple videos
  (signals canonical concepts)
- High-evidence claims — aggregated across the corpus

You walk away with the topic's *evidence-backed* consensus, not the
average creator's vibes.

## 4. Personal learning archive

Every video you watch this year goes through `receipts batch`;
commit the audits to a private git repo:

```bash
mkdir -p ~/learning-vault
cd ~/learning-vault
git init

# Append to today's watch-list, audit overnight
echo "$URL" >> $(date +%Y-%m).urls
receipts batch $(date +%Y-%m).urls --output-dir reports/$(date +%Y-%m)/
git add . && git commit -m "weekly audit"
```

6 months later, query your archive:

```bash
# All HIGH_EVIDENCE videos on machine learning this year
grep -l "HIGH_EVIDENCE" reports/*/*.md | xargs grep -l "machine learning"

# Aggregate verdicts by month
jq -r '.[] | .verdict' reports/2026-04/index.json | sort | uniq -c
```

You now distinguish *"I watched this"* from *"I learned something
verifiable from this"*.

## 5. Topic-evolution tracking

Re-research the same topic every 3 months. Track how the consensus +
evidence quality shifts over time. Useful for fast-moving fields:

```bash
TOPIC="LLM reasoning techniques"
DATE=$(date +%Y-%m)
receipts research "$TOPIC" --n 7 -o "trends/$DATE-llm-reasoning.md"

# 6 months later, diff:
diff trends/2026-04-llm-reasoning.md trends/2026-10-llm-reasoning.md
```

Verdicts shift from MIXED to HIGH_EVIDENCE as a field matures —
that's a useful signal.

## 6. Creator accountability score

Audit a creator's last 20 videos. Average evidence quality →
"channel score". You'll see who consistently shows their work and
who consistently doesn't:

```bash
# Get the channel's last 20 video IDs via yt-dlp
yt-dlp --flat-playlist --print "%(id)s" \
       "https://www.youtube.com/@CHANNEL_NAME/videos" \
   | head -20 | sed 's|^|https://youtu.be/|' > channel_urls.txt

receipts batch channel_urls.txt --output-dir channel_audits/

# Score: percent of videos with at least MIXED evidence
jq -r '.[] | .verdict' channel_audits/index.json \
  | awk '/HIGH_EVIDENCE|MIXED/{good++} END{print good"/" NR}'
```

Trust calibrated by data.

## 7. Pre-syllabus generator

Research a topic, extract the high-evidence claims, output a
structured "here's what you'd learn" outline *before* watching
anything:

```bash
receipts research "transformers attention mechanism" --n 5 -o syllabus.md
```

The "High-evidence claims across the topic" section in the report
becomes your study guide. Watch only video #1 (the best-evidence
one); use the syllabus to fill in the gaps.

## 8. News-event cross-check

For breaking news, political commentary, or anything controversial:
research the same topic across many creators. Surface where they
agree, where they diverge, what each cites:

```bash
receipts research "Iran economy 2026 sanctions" --n 8 --domain political
```

The consensus terms section shows what *most* creators agree on; the
high-evidence section shows which ones cite specific data; the
reading order shows which to actually trust.

## 9. Paper-explanation ranker

Famous paper just dropped, you want to understand it. There's
already 30 "[paper] explained" videos. Which is worth watching?

```bash
receipts research "attention is all you need explained" --n 7
```

The HIGH_EVIDENCE one engages with the math. The LOW_EVIDENCE ones
are hand-wavy. Pick the one that does both: explains the intuition
*and* shows the equations + citations.

## 10. Anti-grift filter for finance content

Finance / trading / crypto YouTube is 95% influencer noise. Use
`receipts` as the filter:

```bash
receipts batch finance_queue.txt --domain trading \
       --output-dir audits/

# Alert me when something's actually got numbers + citations
jq -r '.[] | select(.verdict == "HIGH_EVIDENCE" or .verdict == "MIXED") |
        "\(.verdict)\t\(.url)\t\(.title)"' audits/index.json
```

You watch the 5% that has receipts. Skip the 95% that doesn't. Years
of due diligence collapsed into a daily filter pipeline.

## The unifying pattern

Every use case above is a variant of:

> *"I'd otherwise watch N videos to make a decision. Replace with: N
> audits + watching the top 1-2."*

Time saved: ~80%. Confidence: way higher (you're picking based on
evidence quality, not video thumbnails or recency). And the audits
become a permanent, queryable artifact — your future self can answer
*"what did I actually learn from that fasting video three months ago?"*
in 30 seconds.
