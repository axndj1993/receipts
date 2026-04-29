"""receipts CLI.

Subcommands:
  fetch URL           — download metadata + raw VTT, print paths
  transcribe URL      — clean transcript only, print to stdout
  audit URL           — full evidence audit, write Markdown report
  batch FILE          — audit a list of URLs (one per line)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import audit, SkeletonVetter
from .fetcher import FetchError, fetch_video
from .transcript import clean_vtt


def _cmd_fetch(args: argparse.Namespace) -> int:
    meta, raw_vtt = fetch_video(args.url, workdir=args.workdir, keep_files=True)
    print(f"video_id     : {meta.video_id}")
    print(f"title        : {meta.title}")
    print(f"channel      : {meta.channel}")
    print(f"upload_date  : {meta.upload_date}")
    print(f"duration     : {meta.duration_pretty}")
    print(f"vtt size     : {len(raw_vtt):,} chars")
    return 0


def _cmd_transcribe(args: argparse.Namespace) -> int:
    meta, raw_vtt = fetch_video(args.url)
    t = clean_vtt(raw_vtt)
    if args.json:
        out = {
            "video_id": meta.video_id,
            "title": meta.title,
            "channel": meta.channel,
            "upload_date": meta.upload_date,
            "duration_seconds": meta.duration_seconds,
            "word_count": t.word_count,
            "text": t.text,
            "cues": t.cues,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(t.text)
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    report = audit(args.url, domain=args.domain)
    md = report.to_markdown()
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(md)
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    src = Path(args.urls_file)
    if not src.exists():
        print(f"error: {src} not found", file=sys.stderr)
        return 2
    urls = [ln.strip() for ln in src.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    for url in urls:
        try:
            report = audit(url, domain=args.domain)
        except FetchError as e:
            print(f"FAIL  {url}  ({e})", file=sys.stderr)
            summary.append({"url": url, "error": str(e)})
            continue
        slug = report.metadata.video_id or _slug(url)
        path = out_dir / f"{slug}.md"
        path.write_text(report.to_markdown(), encoding="utf-8")
        n_claims = len(report.claims)
        print(f"OK    {url}  ({report.verdict}, {n_claims} claims)  -> {path}")
        summary.append({
            "url": url,
            "video_id": report.metadata.video_id,
            "title": report.metadata.title,
            "channel": report.metadata.channel,
            "verdict": report.verdict,
            "n_claims": n_claims,
            "report_path": str(path),
        })
    (out_dir / "index.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out_dir / 'index.json'}", file=sys.stderr)
    return 0


def _slug(url: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")[:40]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="receipts",
        description="YouTube evidence-audit tool.",
    )
    p.add_argument("--version", action="version", version=f"receipts {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="download metadata + raw VTT")
    p_fetch.add_argument("url")
    p_fetch.add_argument("--workdir", default=None,
                         help="where to leave fetched files (default: tmp)")
    p_fetch.set_defaults(func=_cmd_fetch)

    p_tr = sub.add_parser("transcribe", help="clean transcript to stdout")
    p_tr.add_argument("url")
    p_tr.add_argument("--json", action="store_true",
                      help="emit JSON with metadata + cues")
    p_tr.set_defaults(func=_cmd_transcribe)

    p_au = sub.add_parser("audit", help="evidence audit (Markdown report)")
    p_au.add_argument("url")
    p_au.add_argument("--domain", default="general",
                      help="hint for the vetter (trading/health/general)")
    p_au.add_argument("-o", "--output", default=None,
                      help="write report to file instead of stdout")
    p_au.set_defaults(func=_cmd_audit)

    p_bt = sub.add_parser("batch", help="audit a list of URLs from a file")
    p_bt.add_argument("urls_file",
                      help="file with one URL per line (# comments OK)")
    p_bt.add_argument("--domain", default="general")
    p_bt.add_argument("--output-dir", default="receipts_reports",
                      help="output dir for per-video reports + index.json")
    p_bt.set_defaults(func=_cmd_batch)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except FetchError as e:
        print(f"receipts: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
