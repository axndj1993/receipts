# Installation

## Requirements

- Python 3.10 or later
- `yt-dlp` (installed automatically as a dependency)
- Internet access (yt-dlp fetches the captions from YouTube)

## Install

```bash
pip install receipts
```

Or, from this repo:

```bash
git clone https://github.com/<org>/<repo>.git
cd <repo>
pip install -e .
```

For dev (pytest):

```bash
pip install -e ".[dev]"
```

## Verify

```bash
receipts --version
# receipts 0.1.0

receipts fetch https://youtu.be/0L6Rcgp6j7Y
# video_id     : 0L6Rcgp6j7Y
# title        : Four Price Action Secrets ...
# channel      : TradingLab
# upload_date  : 20211022
# duration     : 8m 10s
# vtt size     : 76,045 chars
```

If `fetch` succeeds, you're set up. The first time may take a few
seconds while yt-dlp probes YouTube; subsequent calls cache nothing
locally (receipts always pulls fresh — captions can be edited).

## Optional: ffmpeg

receipts **never** downloads the video itself, so ffmpeg is not required.
yt-dlp may emit a warning about ffmpeg being missing — you can ignore it.

## Uninstall

```bash
pip uninstall receipts
```

receipts writes nothing to your home directory or system config.
Reports go where you point them (`-o`, `--output-dir`).
