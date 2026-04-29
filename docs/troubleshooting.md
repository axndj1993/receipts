# Troubleshooting

## `FetchError: yt-dlp not found on PATH`

```bash
pip install yt-dlp
# or, since yt-dlp is a receipts dependency, just:
pip install -e .
```

## `FetchError: yt-dlp exit 1: ERROR: ...`

Most common causes:

1. **YouTube changed their player.** yt-dlp updates frequently for this
   reason. Update:

   ```bash
   pip install -U yt-dlp
   ```

2. **No JavaScript runtime.** yt-dlp warns about this; install Deno or
   Node:

   ```bash
   # macOS
   brew install deno

   # Ubuntu
   curl -fsSL https://deno.land/install.sh | sh
   ```

3. **Region/age block.** Some videos are unavailable from your IP or
   require sign-in. yt-dlp has flags for cookies (`--cookies`,
   `--cookies-from-browser`); receipts doesn't expose them in v0.1.
   You can pre-fetch with raw `yt-dlp` and call
   `clean_vtt` + `SkeletonVetter().vet(...)` directly.

## `FetchError: no en subtitles found`

The video has captions disabled, or only in non-English. Try:

```bash
yt-dlp --list-subs https://youtu.be/<id>
```

If only `--write-auto-sub` shows nothing, YouTube hasn't generated
captions. There's no transcript to audit.

If a different language is available, receipts v0.1 doesn't expose
`sub_lang` via CLI yet — call the Python API:

```python
from receipts.fetcher import fetch_video
from receipts.transcript import clean_vtt
from receipts.audit import SkeletonVetter

meta, raw_vtt = fetch_video(url, sub_lang="es")
transcript = clean_vtt(raw_vtt)
report = SkeletonVetter().vet(meta, transcript, domain="general")
```

## Audit returns ONE giant claim instead of many

This used to happen on auto-captioned videos (no punctuation → sentence
splitter returned one blob). receipts 0.1+ has a fallback that chunks
unpunctuated text into fixed-word groups. If you're still seeing it,
you're on an older version — upgrade:

```bash
pip install -U receipts
```

## Verdict feels wrong (e.g. "HIGH_EVIDENCE" on a vibes video)

The skeleton vetter is rule-based and has known false positives:

- Heavy use of conditional words ("when you see X, then Y") inflates
  the `is_testable` flag without actually testing anything.
- Embedded prices ("at $4500", "around 5%") inflate `has_number` even
  when not making a quantitative claim.

For nuance, use an LLM-backed vetter. The skeleton is a baseline, not
the final word. See [architecture](architecture.md#extension-points).

## Audit takes too long

The bottleneck is yt-dlp's network call. Typical fetch is 3-10 seconds.
For batches:

- **Run sequentially** in the foreground — keeps things simple.
- **Parallelize at the OS level** with `xargs -P 4` if you trust
  YouTube to not rate-limit you.

The audit step itself (transcript clean + skeleton vetter) is <50ms
per video.

## Output Markdown breaks in my renderer

The transcript section is wrapped in a triple-backtick block. If your
Markdown renderer chokes on lowercase-only text inside triple backticks
(uncommon but happens), edit the report or post-process:

```python
md = report.to_markdown().replace("```\n", "<pre>\n").replace("\n```", "\n</pre>")
```

## Memory growth when batching many videos

yt-dlp keeps the info-json in RAM during a fetch (~1MB). With
`keep_files=False` (default) the temp files are cleaned per call. If
you batch 1000+ videos in one Python process, you may want to recycle
the process every 100 to release any pinned memory:

```bash
xargs -n 100 receipts batch -- urls.txt
```
