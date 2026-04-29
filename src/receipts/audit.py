"""Audit pipeline: video → claims → evidence assessment → report."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .fetcher import VideoMetadata, fetch_video
from .transcript import Transcript, clean_vtt


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------
@dataclass
class Claim:
    """A single claim extracted from the transcript."""
    text: str
    has_number: bool
    has_source: bool
    is_testable: bool
    notes: str = ""

    @property
    def evidence_score(self) -> int:
        """0..3, summed from has_number / has_source / is_testable."""
        return int(self.has_number) + int(self.has_source) + int(self.is_testable)


@dataclass
class AuditReport:
    """Full evidence audit of one video."""
    metadata: VideoMetadata
    transcript: Transcript
    claims: list[Claim] = field(default_factory=list)
    domain: str = "general"
    verdict: str = ""           # one of: HIGH_EVIDENCE / MIXED / LOW_EVIDENCE / UNSUPPORTED
    summary: str = ""           # short paragraph-style summary
    notes: str = ""             # vetter-side commentary (recommendations, caveats)

    def to_markdown(self) -> str:
        """Render a Markdown audit report."""
        m = self.metadata
        out: list[str] = []
        out.append(f"# Audit: {m.title}")
        out.append("")
        out.append(f"**Channel:** {m.channel}  ")
        out.append(f"**Uploaded:** {m.upload_date or 'unknown'}  ")
        out.append(f"**Duration:** {m.duration_pretty}  ")
        if m.view_count is not None:
            out.append(f"**Views:** {m.view_count:,}  ")
        out.append(f"**URL:** {m.url}")
        out.append("")
        out.append(f"**Verdict:** `{self.verdict or 'UNCLASSIFIED'}` "
                   f"(domain: {self.domain})")
        out.append("")
        if self.summary:
            out.append("## Summary")
            out.append("")
            out.append(self.summary)
            out.append("")
        out.append(f"## Claims ({len(self.claims)})")
        out.append("")
        if not self.claims:
            out.append("*No claims extracted (skeleton vetter or empty "
                       "transcript).*")
            out.append("")
        else:
            out.append("| # | Claim | Number? | Source? | Testable? | Score |")
            out.append("|---|-------|---------|---------|-----------|-------|")
            for i, c in enumerate(self.claims, 1):
                tx = c.text.replace("|", "\\|")
                if len(tx) > 140:
                    tx = tx[:137] + "..."
                out.append(
                    f"| {i} | {tx} | {'Y' if c.has_number else 'N'} | "
                    f"{'Y' if c.has_source else 'N'} | "
                    f"{'Y' if c.is_testable else 'N'} | {c.evidence_score}/3 |"
                )
            out.append("")
        if self.notes:
            out.append("## Vetter notes")
            out.append("")
            out.append(self.notes)
            out.append("")
        out.append("## Transcript")
        out.append("")
        out.append(f"({self.transcript.word_count} words)")
        out.append("")
        out.append("```")
        out.append(self.transcript.text)
        out.append("```")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Vetter protocol — pluggable
# ---------------------------------------------------------------------------
class Vetter(Protocol):
    """A vetter takes the metadata + transcript and produces an assessment.

    Implementations can:
      - rule-based (SkeletonVetter): no LLM, fast, deterministic
      - LLM-backed: claim extraction via LLM call, optional web search
      - domain-specialized: TradingVetter knows what 'real backtest
        evidence' looks like, HealthVetter knows clinical-trial
        standards, etc.
    """

    def vet(self, metadata: VideoMetadata,
            transcript: Transcript, *, domain: str) -> AuditReport: ...


# ---------------------------------------------------------------------------
# SkeletonVetter — no LLM, rule-based, useful as a baseline + offline mode
# ---------------------------------------------------------------------------
_NUMBER_RE = re.compile(
    r"\b\d+(\.\d+)?%?\b|"           # 5, 5.4, 5%
    r"\b\d+(?:\.\d+)?\s*(?:x|X)\b|" # 2x, 1.5x
    r"\$\d+(?:,\d{3})*(?:\.\d+)?"   # $1,500.00
)
_SOURCE_RE = re.compile(
    r"\b(?:study|paper|research|published|peer[-\s]?reviewed|"
    r"according to|backtest(?:ed)?|sample size|n\s*=\s*\d+|"
    r"out[-\s]?of[-\s]?sample|oos|sharpe|win[\s-]?rate)\b",
    re.IGNORECASE,
)
_TESTABLE_RE = re.compile(
    r"\b(?:if|when|always|never|every|whenever|condition|rule|"
    r"setup|trigger|signal|threshold)\b",
    re.IGNORECASE,
)


def _split_sentences(text: str, *, fallback_chunk_words: int = 40) -> list[str]:
    """Split a transcript into claim-sized chunks.

    YouTube auto-captions have no punctuation (one long lowercase
    blob), so the standard `.!?` splitter returns nothing useful. When
    we detect low punctuation density, we fall back to fixed-word
    chunking — every `fallback_chunk_words` consecutive words become
    one synthetic "sentence" for scoring.

    The threshold (≥ 1 sentence break per ~50 words) matches typical
    spoken English; videos with manual captions usually clear it
    easily.
    """
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    parts = [p.strip() for p in parts if len(p.strip()) > 20]
    n_words = len(text.split())
    has_real_sentences = (
        len(parts) > 1 and n_words > 0 and (n_words / len(parts)) <= 50
    )
    if has_real_sentences:
        return parts
    # Fallback: chunk by N words.
    words = text.split()
    chunks: list[str] = []
    for i in range(0, len(words), fallback_chunk_words):
        chunk = " ".join(words[i : i + fallback_chunk_words])
        if len(chunk) > 20:
            chunks.append(chunk)
    return chunks


class SkeletonVetter:
    """Rule-based vetter — runs offline, no LLM call.

    Extracts sentences that look like *claims* (declarative, longer than
    20 chars), scores each by:
      - has_number: contains a quantitative figure (percent, multiple, $, n=)
      - has_source: cites a source (study, paper, n=N, sharpe, OOS)
      - is_testable: declarative + conditional language ("when X, do Y")

    Aggregates to a verdict:
      - HIGH_EVIDENCE  — avg score >= 2.0
      - MIXED          — avg score 1.0..2.0
      - LOW_EVIDENCE   — avg score 0.5..1.0
      - UNSUPPORTED    — avg score < 0.5

    Designed as a sanity-baseline; serious audits should plug in an
    LLM-backed Vetter that does proper claim extraction + cross-
    referencing against external evidence.
    """

    def __init__(self, max_claims: int = 30) -> None:
        self.max_claims = max_claims

    def vet(self, metadata: VideoMetadata, transcript: Transcript,
            *, domain: str) -> AuditReport:
        sents = _split_sentences(transcript.text)
        claims: list[Claim] = []
        for s in sents:
            has_number = bool(_NUMBER_RE.search(s))
            has_source = bool(_SOURCE_RE.search(s))
            is_testable = bool(_TESTABLE_RE.search(s))
            # A sentence is a claim if it scores on at least one of the
            # three axes — pure narration ("the market is exciting!")
            # contributes nothing and is filtered out.
            if not (has_number or has_source or is_testable):
                continue
            claims.append(Claim(text=s, has_number=has_number,
                                has_source=has_source, is_testable=is_testable))
            if len(claims) >= self.max_claims:
                break

        if claims:
            avg = sum(c.evidence_score for c in claims) / len(claims)
        else:
            avg = 0.0

        # Verdict thresholds tuned so:
        #   - Pure-vibes transcripts (avg ≈ 1.0, all single-axis claims)
        #     come out LOW_EVIDENCE rather than MIXED.
        #   - HIGH_EVIDENCE requires multiple axes per claim on average.
        verdict = (
            "HIGH_EVIDENCE" if avg >= 2.5
            else "MIXED" if avg >= 1.8
            else "LOW_EVIDENCE" if avg >= 0.5
            else "UNSUPPORTED"
        )

        return AuditReport(
            metadata=metadata,
            transcript=transcript,
            claims=claims,
            domain=domain,
            verdict=verdict,
            summary=transcript.excerpt(800),
            notes=(
                f"Skeleton vetter (rule-based, no LLM). Scored {len(claims)} "
                f"claim-like sentences with avg evidence score {avg:.2f}/3. "
                "For deeper audits, plug in an LLM-backed Vetter that does "
                "proper claim extraction + external evidence checks."
            ),
        )


# ---------------------------------------------------------------------------
# Top-level audit() helper
# ---------------------------------------------------------------------------
def audit(
    url: str,
    *,
    domain: str = "general",
    vetter: Vetter | None = None,
    keep_files: bool = False,
) -> AuditReport:
    """One-shot pipeline: URL → fetched + cleaned + vetted AuditReport.

    Args:
        url: YouTube URL.
        domain: optional hint for the vetter ("trading", "health", ...).
        vetter: a Vetter implementation. Defaults to SkeletonVetter().
        keep_files: leave yt-dlp's tmp files on disk for debugging.

    Returns the populated AuditReport. Use `.to_markdown()` to render.
    """
    meta, raw_vtt = fetch_video(url, keep_files=keep_files)
    transcript = clean_vtt(raw_vtt)
    v = vetter or SkeletonVetter()
    return v.vet(meta, transcript, domain=domain)
