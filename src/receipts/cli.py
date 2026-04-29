"""receipts CLI.

Subcommands:
  fetch URL           — download metadata + raw VTT, print paths
  transcribe URL      — clean transcript only, print to stdout
  audit URL           — full evidence audit, write Markdown report
  batch FILE          — audit a list of URLs (one per line)
  research TOPIC      — find + audit + synthesize the top N videos on a topic
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import audit, SkeletonVetter
from .fetcher import FetchError, fetch_video
from .research import ResearchError, research
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


def _cmd_research(args: argparse.Namespace) -> int:
    try:
        report = research(args.topic, n=args.n, domain=args.domain)
    except ResearchError as e:
        print(f"receipts: research error: {e}", file=sys.stderr)
        return 1
    md = report.to_markdown()
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(md)
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for r in report.audits:
            slug = r.metadata.video_id or _slug(r.metadata.url)
            (out_dir / f"{slug}.md").write_text(
                r.to_markdown(), encoding="utf-8")
        (out_dir / "research.md").write_text(md, encoding="utf-8")
        (out_dir / "index.json").write_text(json.dumps([
            {
                "video_id": r.metadata.video_id,
                "title": r.metadata.title,
                "channel": r.metadata.channel,
                "url": r.metadata.url,
                "verdict": r.verdict,
                "n_claims": len(r.claims),
            }
            for r in report.audits
        ], indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote per-video reports + index.json -> {out_dir}",
              file=sys.stderr)
    return 0


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

    p_rs = sub.add_parser(
        "research",
        help="find + audit + synthesize the top N YouTube videos on a topic",
    )
    p_rs.add_argument("topic", help="topic to research (e.g. 'TSMOM strategies')")
    p_rs.add_argument("--n", type=int, default=5,
                      help="number of top videos to audit (default 5)")
    p_rs.add_argument("--domain", default="general")
    p_rs.add_argument("-o", "--output", default=None,
                      help="write the cross-video research report to this file")
    p_rs.add_argument("--output-dir", default=None,
                      help="also write per-video reports + index.json here")
    p_rs.set_defaults(func=_cmd_research)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except FetchError as e:
        print(f"receipts: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
