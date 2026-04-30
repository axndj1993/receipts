"""receipts — turn any YouTube video into an evidence-audit Markdown report.

Most "summarize this video" tools paraphrase the speaker. receipts does the
opposite: it extracts the speaker's *claims*, then assesses each one
against quality criteria (does the claim have a number? a source? a
testable mechanism?), producing a brutally honest audit.

Useful for:

  * Vetting "trading guru" / "health expert" / "tech reviewer" videos
    before adopting their advice.
  * Building a personal knowledge base that distinguishes "I watched
    this" from "I learned something verifiable from this".
  * Quickly comparing N videos on a topic — which actually has data,
    which is just confidence?

Quickstart:

    from receipts import audit
    report = audit("https://youtu.be/0L6Rcgp6j7Y", domain="trading")
    print(report.to_markdown())

Or:

    receipts audit https://youtu.be/0L6Rcgp6j7Y --domain trading -o audit.md

CLI:

    receipts fetch URL                   # download transcript + metadata only
    receipts transcribe URL              # clean transcript to stdout
    receipts audit URL [--domain X]      # full evidence audit
    receipts batch FILE                  # batch audit a list of URLs
    receipts research TOPIC --n 5        # find + audit + synthesize across N videos
"""
from __future__ import annotations

from .fetcher import VideoMetadata, fetch_video, FetchError
from .transcript import clean_vtt, Transcript
from .audit import audit, AuditReport, Vetter, SkeletonVetter
from .research import research, ResearchReport, ResearchError

__all__ = [
    "audit",
    "AuditReport",
    "VideoMetadata",
    "Transcript",
    "fetch_video",
    "clean_vtt",
    "Vetter",
    "SkeletonVetter",
    "FetchError",
    "research",
    "ResearchReport",
    "ResearchError",
]
__version__ = "0.4.0"
