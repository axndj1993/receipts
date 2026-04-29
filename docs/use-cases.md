# Use cases

Anywhere you'd otherwise watch 5–10 videos to learn or evaluate a
topic, `receipts` compresses the decision-making to ~30 seconds + 1
actual watch.

This page organizes the patterns by **who you are** — pick the
section closest to your role, copy-paste the snippet, run.

---

## 🎓 Student

YouTube has become a default learning channel alongside textbooks +
papers, but the signal-to-noise is brutal. `receipts` lets you spot
the actually-rigorous videos before committing study time.

### Build a study guide before watching

Find the best videos on a concept; their high-evidence claims
become your pre-syllabus:

```bash
receipts research "transformers attention mechanism" --n 7 -o syllabus.md
```

Watch the top-1 (HIGH_EVIDENCE), use the synthesis section to
back-fill gaps. ~30 minutes vs ~3 hours of trial-and-error
watching.

### Cross-check a textbook claim

Your textbook says X about Y. Find what YouTube creators actually
cite:

```bash
receipts research "<the textbook claim verbatim>" --n 5
```

Look for the consensus terms section — those are the canonical
concepts. Anything in the high-evidence claims that contradicts the
textbook is worth flagging to your instructor.

### Compare professors / lecturers explaining the same concept

Five "explained" videos for backpropagation? Audit them:

```bash
echo "https://youtu.be/<creator-A>" >  bp_urls.txt
echo "https://youtu.be/<creator-B>" >> bp_urls.txt
echo "https://youtu.be/<creator-C>" >> bp_urls.txt
echo "https://youtu.be/<creator-D>" >> bp_urls.txt
echo "https://youtu.be/<creator-E>" >> bp_urls.txt
receipts batch bp_urls.txt --output-dir bp_audits/

# Best evidence first
jq -r '.[] | "\(.verdict)\t\(.title)\t\(.channel)"' bp_audits/index.json | sort
```

You watch the one that engages with the math; skip the four that
hand-wave.

### Pre-screen paid courses / bootcamps

A $200-2000 course has free preview lessons. Audit those first:

```bash
receipts audit "https://youtu.be/<preview-id>" --domain education
```

LOW_EVIDENCE preview = the paid content probably isn't better.

---

## 💻 Developer

YouTube is overflowing with framework / tool / language tutorials.
Most are hyped, few survive a code-walk. `receipts` filters.

### "Should I learn X?" research

Before investing weeks in a new framework:

```bash
receipts research "Bun vs Node.js performance benchmarks" --n 7
```

The high-evidence claims tell you who actually shows numbers vs
who's marketing.

### Tutorial-quality filter

You've bookmarked 30 React tutorials. Audit them:

```bash
receipts batch react_tutorials.txt --output-dir react_audits/
jq -r '.[] | select(.verdict == "MIXED" or .verdict == "HIGH_EVIDENCE") | .url' \
    react_audits/index.json
```

Watch only those URLs.

### Conference talk pre-screen

NeurIPS / RustConf / KubeCon dropped 200 talks. Audit the ones in
your area:

```bash
receipts batch conf_talks.txt --output-dir conf_audits/
```

Watch HIGH_EVIDENCE first; skim MIXED if relevant; skip the rest.

### "What's the gotcha?" research

You're about to integrate a third-party SDK. Find the post-mortem
videos:

```bash
receipts research "Stripe API gotchas in production" --n 5
```

Other developers' real failures, surfaced first.

---

## 🤖 AI Engineer

The AI/ML YouTube ecosystem is uniquely noisy — every model
release spawns 50 explainer videos within a week, most of which
hand-wave the math. Receipts cuts the noise.

### Paper explanation ranker

A paper drops; you want to understand it without spending 6 hours
on a slow read:

```bash
receipts research "attention is all you need explained" --n 7 -o aiayn.md
```

The HIGH_EVIDENCE one walks the equations; LOW_EVIDENCE ones just
say "tokens flow through layers".

### Pre-implementation guide

You're implementing X from scratch. Five "implementing X from
scratch" tutorials exist. Which actually shows the code vs which
is just talking-head:

```bash
receipts research "implementing diffusion models from scratch" --n 7
```

### Track a new model release

Anthropic / OpenAI / Mistral drops a model. Audit the takes within
24 hours:

```bash
receipts research "Claude Opus 4.7 reasoning capabilities" --n 10
```

Reading order shows you which YouTubers actually ran benchmarks vs
which are just guessing.

### Audit an AI influencer's catalog

A creator claims expertise. Pull their last 30 videos, score them:

```bash
yt-dlp --flat-playlist --print "%(id)s" \
       "https://www.youtube.com/@CHANNEL/videos" \
   | head -30 | sed 's|^|https://youtu.be/|' > ch.txt
receipts batch ch.txt --domain ai --output-dir ch_audits/

jq -r '.[] | .verdict' ch_audits/index.json | sort | uniq -c
```

If the channel averages LOW_EVIDENCE, calibrate trust accordingly.

---

## 📈 Trader / Investor

Finance YouTube is famously low-evidence. `receipts` filters with
brutal honesty (we [tested 6 trading-guru videos](../../futures-bot/research/video_archive)
ourselves; verdict: 6/6 LOW_EVIDENCE).

### Anti-grift filter for finance

```bash
receipts batch finance_queue.txt --domain trading \
       --output-dir audits/

# Alert only when something's actually got numbers + citations
jq -r '.[] | select(.verdict == "HIGH_EVIDENCE" or .verdict == "MIXED") |
        "\(.verdict)\t\(.url)\t\(.title)"' audits/index.json
```

Watch the 5% that has receipts. Skip the 95% that doesn't.

### Strategy backtest videos

YouTuber claims "70% WR strategy". Audit if they actually show:

```bash
receipts audit "https://youtu.be/<strategy-vid>" --domain trading
```

If `has_source = N` for every claim → no real backtest. Move on.

### Macro / sector research

You're sizing a position in a sector. Cross-check the loud voices:

```bash
receipts research "semiconductor cycle 2026 outlook" --domain finance --n 8
```

Consensus terms = canonical narrative. High-evidence claims = which
analysts cite specific data vs vibe.

### Founder podcast audit

A founder is on five podcasts pitching numbers. Audit them all:

```bash
receipts batch founder_podcasts.txt --domain finance
```

Numbers should match across podcasts. If they don't, that's signal.

---

## 🔬 Researcher / Scientist

### Literature review supplementation

Lay-explanations of a paper are sometimes more digestible than the
paper itself. Find the best one:

```bash
receipts research "RLHF reward hacking failure modes" --n 5
```

### Pre-print explanations

A pre-print drops; YouTube creators rush to "explain" it. Filter
for the rigorous ones before the consensus forms.

### Conference recap reliability

NeurIPS / ICML recap videos on YouTube. Some are deep, most are
shallow. Audit before relying on them:

```bash
receipts batch neurips_recaps.txt --domain ai --output-dir recaps/
```

---

## 👨‍🏫 Educator / Teacher

### Build a custom syllabus from YouTube

You're teaching X. Curate the best YouTube videos by topic:

```bash
for topic in "intro" "applications" "edge cases" "advanced"; do
    receipts research "$topic of <subject>" --n 5 -o syllabus/$topic.md
done
```

Hand the reading-order to students.

### Spot-check student-shared sources

Student says "this YouTube video says X". Don't argue from authority
— audit:

```bash
receipts audit "<student URL>" --domain education
```

Use the verdict + claims table as the conversation starter.

---

## 💼 Investor (VC / angel)

### Founder accountability scorecard

Audit a founder's last 10 podcast/conference appearances. Track if
their claimed numbers stay consistent:

```bash
receipts batch founder_appearances.txt --domain business
diff founder_audits/2025-Q1.md founder_audits/2026-Q2.md
```

### Sector-thesis cross-check

Five thought-leaders in your target sector. Where do they agree?
Where do they diverge? Who cites data?

```bash
receipts research "vertical SaaS 2026 trends" --domain business --n 7
```

---

## 📰 Journalist / Researcher

### Source verification

Video makes a claim. Cited?

```bash
receipts audit "<video URL>"
# claims table → has_source column → if N for all, treat as opinion
```

### Channel accountability

A channel makes lots of claims. Audit their catalog:

```bash
yt-dlp --flat-playlist --print "%(id)s" \
       "https://www.youtube.com/@CHANNEL/videos" \
   | head -50 | sed 's|^|https://youtu.be/|' > ch.txt
receipts batch ch.txt --output-dir ch_audits/
```

The aggregate verdict distribution tells you whether the channel is
worth citing as a source.

---

## 💪 Health & fitness

Diet / exercise / supplement YouTube is famously evidence-light.
Receipts is your pre-watch firewall.

### Supplement evaluation

```bash
receipts research "creatine cognitive benefits clinical trials" \
    --domain health --n 7
```

### Diet protocol cross-check

Five creators all claim X works. Audit:

```bash
receipts batch diet_videos.txt --domain health --output-dir diet/
```

The HIGH_EVIDENCE creator is probably citing actual studies.

---

## 🎯 Generic self-learner / autodidact

### Watch-later queue triage

You bookmark too much. Audit weekly, sort by verdict, watch top
20%:

```bash
receipts batch watch_later.txt --output-dir queue/
jq -r '.[] | "\(.verdict)\t\(.title)"' queue/index.json | sort
```

### Personal learning archive

Every video you watch goes through receipts. Commit audits to a
private git repo. Months later, query:

```bash
grep -l "HIGH_EVIDENCE" archive/*/*.md | xargs grep -l "machine learning"
```

= every HIGH_EVIDENCE video on ML you've watched. Not a YouTube
history list — a curated, evidence-graded learning corpus.

### Topic-evolution tracking

Re-research the same topic every 3 months; track how consensus +
evidence quality shifts. Useful for fast-moving fields:

```bash
TOPIC="LLM agent design patterns"
DATE=$(date +%Y-%m)
receipts research "$TOPIC" --n 7 -o "trends/$DATE.md"
```

6 months later, diff the snapshots. Verdicts shifting from MIXED to
HIGH_EVIDENCE = field maturing.

---

## The unifying pattern

Every persona above does a variant of:

> *"I'd otherwise watch N videos to make a decision. Replace with: N
> audits + watching the top 1–2."*

Time saved: ~80%. Confidence: way higher (you're picking on
evidence quality, not thumbnails). And the audits become a
permanent, queryable artifact — your future self can answer *"what
did I actually learn from that fasting video three months ago?"*
in 30 seconds.

That's the lasting value: receipts isn't just a filter, it's a
**knowledge accountability layer** for the YouTube-as-textbook era.
