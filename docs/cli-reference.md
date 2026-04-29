# CLI reference

`receipts <subcommand> [options]`

## `receipts fetch URL [options]`

Download metadata + raw VTT, print a one-line summary.

| Option       | Default | Meaning |
|--------------|---------|---------|
| `URL`        | required| YouTube URL |
| `--workdir`  | tmp     | where to leave fetched files (forces `keep_files=True`) |

```bash
receipts fetch https://youtu.be/0L6Rcgp6j7Y --workdir ./yt_cache
```

## `receipts transcribe URL [options]`

Print the cleaned transcript to stdout.

| Option   | Default | Meaning |
|----------|---------|---------|
| `URL`    | required| YouTube URL |
| `--json` | off     | emit JSON with metadata + per-cue timestamps |

```bash
receipts transcribe https://youtu.be/0L6Rcgp6j7Y > transcript.txt
receipts transcribe https://youtu.be/0L6Rcgp6j7Y --json | jq .word_count
```

## `receipts audit URL [options]`

Run the full audit pipeline. Outputs Markdown.

| Option        | Default     | Meaning |
|---------------|-------------|---------|
| `URL`         | required    | YouTube URL |
| `--domain`    | `general`   | hint for the vetter |
| `-o`/`--output`| stdout     | write report to a file instead |

```bash
receipts audit https://youtu.be/0L6Rcgp6j7Y --domain trading -o audit.md
```

## `receipts batch FILE [options]`

Audit a list of URLs. Produces one Markdown report per video plus a
consolidated `index.json` with verdicts.

| Option           | Default            | Meaning |
|------------------|--------------------|---------|
| `FILE`           | required           | text file, one URL per line. Lines starting with `#` are comments. |
| `--domain`       | `general`          | hint for the vetter (applies to all URLs) |
| `--output-dir`   | `receipts_reports`   | directory for per-video `.md` + `index.json` |

```bash
receipts batch urls.txt --domain trading --output-dir reports/
```

Failed URLs are recorded in `index.json` with an `error` field; the
batch continues past failures.

## `receipts --version`

Print the receipts version and exit.

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | success |
| 1    | fetch / runtime error (yt-dlp failure, no captions, etc.) |
| 2    | invalid arguments |
