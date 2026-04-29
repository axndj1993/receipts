# Python API reference

```python
from receipts import audit, AuditReport, VideoMetadata, Transcript, Vetter, SkeletonVetter
from receipts.fetcher import fetch_video, FetchError
from receipts.transcript import clean_vtt
```

## `audit(url, *, domain="general", vetter=None, keep_files=False) -> AuditReport`

The one-shot top-level helper. Fetches metadata + captions, cleans
the transcript, runs the vetter, returns a populated `AuditReport`.

| Arg          | Type           | Default            | Meaning |
|--------------|----------------|--------------------|---------|
| `url`        | `str`          | required           | YouTube URL or `youtu.be` short link |
| `domain`     | `str`          | `"general"`        | hint for the vetter ("trading", "health", "tech", ...) |
| `vetter`     | `Vetter`/None  | `SkeletonVetter()` | pluggable scoring backend |
| `keep_files` | `bool`         | `False`            | leave yt-dlp tmp files on disk for debugging |

Raises `FetchError` if yt-dlp fails or the video has no captions.

## `class VideoMetadata` (dataclass)

| Field              | Type        | Meaning |
|--------------------|-------------|---------|
| `video_id`         | `str`       | YouTube ID |
| `url`              | `str`       | input URL |
| `title`            | `str`       | video title (or `"(untitled)"`) |
| `channel`          | `str`       | uploader/channel name (or `"(unknown)"`) |
| `upload_date`      | `str`       | YYYYMMDD as yt-dlp emits |
| `duration_seconds` | `int`       | duration |
| `view_count`       | `int`/None  | views |
| `like_count`       | `int`/None  | likes |
| `description`      | `str`       | full description |
| `categories`       | `list[str]` | YouTube categories |
| `tags`             | `list[str]` | tags |
| `chapters`         | `list[dict]`| video chapters with start times |
| `raw`              | `dict`      | full yt-dlp info-json (escape hatch) |

Property: `duration_pretty` returns "8m 10s" / "1h 23m".

`VideoMetadata.from_info_json(info, url)` — class method for tests / advanced use.

## `class Transcript` (dataclass)

| Field   | Type                            | Meaning |
|---------|---------------------------------|---------|
| `text`  | `str`                           | cleaned, deduped, lowercase transcript |
| `cues`  | `list[tuple[float, str]]`       | per-cue (start_seconds, line) for citing timecodes |

Property: `word_count`, `excerpt(n_chars=800)`.

## `class Claim` (dataclass)

| Field         | Type   | Meaning |
|---------------|--------|---------|
| `text`        | `str`  | the sentence or chunk being scored |
| `has_number`  | `bool` | contains a quantitative figure (5, 5.4, 5%, 1.5x, $1500) |
| `has_source`  | `bool` | cites a source (study, paper, n=N, OOS, sharpe, win-rate) |
| `is_testable` | `bool` | declarative + conditional ("when X, do Y") |

Property: `evidence_score` — sum of the three flags (0..3).

## `class AuditReport` (dataclass)

| Field        | Type                     | Meaning |
|--------------|--------------------------|---------|
| `metadata`   | `VideoMetadata`          | video info |
| `transcript` | `Transcript`             | cleaned text |
| `claims`     | `list[Claim]`            | extracted claims |
| `domain`     | `str`                    | hint passed in |
| `verdict`    | `str`                    | `HIGH_EVIDENCE` / `MIXED` / `LOW_EVIDENCE` / `UNSUPPORTED` |
| `summary`    | `str`                    | short summary (default: first 800 chars of transcript) |
| `notes`      | `str`                    | vetter commentary |

Method: `to_markdown() -> str` renders a Markdown report.

## `Vetter` protocol

```python
class Vetter(Protocol):
    def vet(
        self,
        metadata: VideoMetadata,
        transcript: Transcript,
        *,
        domain: str,
    ) -> AuditReport: ...
```

Implement this method to plug in any scoring backend (LLM-based,
external APIs, custom regex, etc.). Return a populated `AuditReport`.

## `class SkeletonVetter`

The default rule-based vetter. Constructor takes `max_claims` (default
30). Use it as a baseline; for serious audits, plug in a domain-aware
vetter.

```python
SkeletonVetter(max_claims=30)
```

Verdict thresholds (computed on average evidence_score per claim):

- `HIGH_EVIDENCE` — avg ≥ 2.5
- `MIXED`         — avg ≥ 1.8
- `LOW_EVIDENCE`  — avg ≥ 0.5
- `UNSUPPORTED`   — avg < 0.5 (or zero claims found)

## `clean_vtt(raw_vtt: str) -> Transcript`

Standalone helper — converts a yt-dlp VTT subtitle file (as a string)
into a cleaned `Transcript`. Useful if you've already downloaded
captions via another method.

Drops:
- WEBVTT / Kind: / Language: headers
- Timing lines (`00:00:01.000 --> 00:00:03.000 ...`)
- Pure-numeric cue indices
- Inline timing tags `<00:00:01.000>` and `<c>...</c>`
- Contiguous duplicate lines (yt-dlp auto-captions repeat)

## `fetch_video(url, *, workdir=None, sub_lang="en", keep_files=False) -> tuple[VideoMetadata, str]`

Lower-level helper — calls yt-dlp, returns `(VideoMetadata, raw_vtt_text)`.

Use this if you want to inspect the raw VTT before cleaning, or if you
want to cache captions yourself.

## Errors

```python
class FetchError(Exception):
    """yt-dlp missing, network failure, or no captions in `sub_lang`."""
```

Catch `FetchError` to handle bad URLs / private videos / captionless
videos cleanly.
