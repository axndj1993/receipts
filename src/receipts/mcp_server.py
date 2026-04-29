"""receipts MCP server — exposes the audit pipeline as MCP tools.

Run via:
    receipts-mcp

Configure in any MCP-aware client:

    {
      "mcpServers": {
        "receipts": {
          "command": "receipts-mcp"
        }
      }
    }

The agent can then call `receipts_audit` and `receipts_transcribe`
directly when the user shares a YouTube URL — no glue code, no
intermediate file shuffling.
"""
from __future__ import annotations

import json
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "receipts MCP server requires the 'mcp' package. "
        "Install with: pip install 'receipts[mcp]'"
    ) from e

from .audit import audit
from .fetcher import FetchError, fetch_video
from .transcript import clean_vtt


_mcp = FastMCP("receipts")


@_mcp.tool()
def receipts_audit(url: str, domain: str = "general",
                    max_transcript_chars: int = 6000) -> str:
    """Audit a YouTube video. Extract claims, score by evidence quality.

    Returns a structured assessment of every claim the speaker makes:
    - has_number (5%, 1.5x, n=42, $1500)
    - has_source (study, paper, audited statement, OOS)
    - is_testable (declarative rule with conditions, not vibes)
    Plus a verdict bucket: HIGH_EVIDENCE / MIXED / LOW_EVIDENCE / UNSUPPORTED.

    Use this when the user:
    - Shares a YouTube URL and asks "what's in this?" or "is this any good?"
    - Wants to filter "is this video worth watching?" before committing time.
    - Is comparing multiple videos on the same topic.

    Args:
        url: YouTube URL or `youtu.be` short link.
        domain: optional hint ("trading", "health", "tech", "general").
            The default vetter doesn't branch on this; future
            domain-specialized vetters will.
        max_transcript_chars: cap the returned transcript text length
            to avoid blowing up the agent's context. Default 6000.

    Returns: JSON-encoded report with keys
        {metadata, verdict, claims, transcript_excerpt, notes}.
    """
    try:
        report = audit(url, domain=domain)
    except FetchError as e:
        return json.dumps({"error": str(e)})
    out: dict[str, Any] = {
        "metadata": {
            "video_id": report.metadata.video_id,
            "url": report.metadata.url,
            "title": report.metadata.title,
            "channel": report.metadata.channel,
            "upload_date": report.metadata.upload_date,
            "duration_seconds": report.metadata.duration_seconds,
            "duration_pretty": report.metadata.duration_pretty,
            "view_count": report.metadata.view_count,
        },
        "verdict": report.verdict,
        "claims_count": len(report.claims),
        "claims": [
            {
                "text": c.text,
                "has_number": c.has_number,
                "has_source": c.has_source,
                "is_testable": c.is_testable,
                "evidence_score": c.evidence_score,
            }
            for c in report.claims
        ],
        "notes": report.notes,
        "transcript_excerpt": report.transcript.text[:max_transcript_chars],
        "transcript_truncated": len(report.transcript.text) > max_transcript_chars,
    }
    return json.dumps(out, indent=2)


@_mcp.tool()
def receipts_transcribe(url: str, max_chars: int = 20000) -> str:
    """Fetch + clean the auto-generated transcript of a YouTube video.

    Use this when the user wants the words verbatim, not an audit —
    e.g. for citation, search, or feeding into a different downstream
    LLM step.

    Args:
        url: YouTube URL.
        max_chars: cap returned transcript length. Default 20000 (~3000
            words). Set higher to retrieve full transcripts; set lower
            for low-context budgets.

    Returns: JSON with {video_id, title, channel, duration_seconds,
        word_count, text, truncated}.
    """
    try:
        meta, raw_vtt = fetch_video(url)
    except FetchError as e:
        return json.dumps({"error": str(e)})
    t = clean_vtt(raw_vtt)
    text = t.text
    truncated = False
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True
    return json.dumps({
        "video_id": meta.video_id,
        "title": meta.title,
        "channel": meta.channel,
        "upload_date": meta.upload_date,
        "duration_seconds": meta.duration_seconds,
        "word_count": t.word_count,
        "text": text,
        "truncated": truncated,
    }, indent=2)


def main() -> None:
    """Entry point — runs the MCP server over stdio."""
    _mcp.run()


if __name__ == "__main__":
    main()
