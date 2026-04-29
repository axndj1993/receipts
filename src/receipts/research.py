"""Topic research mode — find N videos on a topic, audit each, synthesize.

Given a topic string, yt-dlp searches YouTube and returns the top N
results. Receipts audits each individually, then a synthesizer
identifies consensus claims, contradictions, and a reading-order
recommendation.

Useful for:

  * Pre-research before diving into a topic ("which YouTube videos on
    intermittent fasting actually cite studies?").
  * Cross-validating claims across creators ("do all 5 of these
    'best 401k strategy' videos agree on the answer?").
  * Building a topic-specific knowledge base in batch.

Output: `ResearchReport` with per-video audits + cross-video synthesis.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field

from .audit import AuditReport, audit
from .fetcher import FetchError


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class ResearchError(Exception):
    """Raised when YouTube search fails."""


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------
@dataclass
class ResearchReport:
    """Cross-video research report on a topic."""
    topic: str
    domain: str
    audits: list[AuditReport] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)   # {url, error}
    consensus_terms: list[tuple[str, int]] = field(default_factory=list)
    high_evidence_audits: list[AuditReport] = field(default_factory=list)

    @property
    def n_videos_audited(self) -> int:
        return len(self.audits)

    @property
    def n_videos_failed(self) -> int:
        return len(self.failures)

    def reading_order(self) -> list[AuditReport]:
        """Best-evidence first — recommended order to spend time."""
        order = ["HIGH_EVIDENCE", "MIXED", "LOW_EVIDENCE", "UNSUPPORTED"]
        return sorted(
            self.audits,
            key=lambda r: (order.index(r.verdict) if r.verdict in order else 99,
                           -len(r.claims)),
        )

    def to_markdown(self) -> str:
        """Render the cross-video research report."""
        out: list[str] = []
        out.append(f"# Research: {self.topic}")
        out.append("")
        out.append(f"**Domain:** {self.domain}  ")
        out.append(f"**Videos audited:** {self.n_videos_audited}  ")
        if self.failures:
            out.append(f"**Videos failed:** {self.n_videos_failed}  ")
        out.append("")
        out.append("## Reading order (best evidence first)")
        out.append("")
        out.append("| Rank | Verdict | Claims | Title | URL |")
        out.append("|------|---------|--------|-------|-----|")
        for i, r in enumerate(self.reading_order(), 1):
            title = r.metadata.title.replace("|", "\\|")
            if len(title) > 60:
                title = title[:57] + "..."
            out.append(
                f"| {i} | `{r.verdict}` | {len(r.claims)} | {title} "
                f"| {r.metadata.url} |"
            )
        out.append("")
        if self.high_evidence_audits:
            out.append("## High-evidence claims across the topic")
            out.append("")
            out.append("Aggregated from the highest-scoring (≥2/3) claims of every "
                       "video. These are the single best 'show me the receipts' "
                       "moments in the corpus.")
            out.append("")
            for r in self.high_evidence_audits:
                high = [c for c in r.claims if c.evidence_score >= 2]
                if not high:
                    continue
                out.append(f"### {r.metadata.title} ({r.verdict})")
                out.append("")
                for c in high[:5]:
                    text = c.text[:200].replace("\n", " ")
                    out.append(f"- ({c.evidence_score}/3) {text}")
                out.append("")
        if self.consensus_terms:
            out.append("## Consensus terms")
            out.append("")
            out.append("Terms appearing across multiple videos — useful for "
                       "spotting shared vocabulary / canonical concepts in the "
                       "topic.")
            out.append("")
            out.append("| Term | Videos |")
            out.append("|------|--------|")
            for term, n in self.consensus_terms[:30]:
                out.append(f"| {term} | {n} |")
            out.append("")
        if self.failures:
            out.append("## Fetch failures")
            out.append("")
            for f in self.failures:
                out.append(f"- `{f['url']}` — {f['error']}")
            out.append("")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def _search_youtube(topic: str, n: int) -> list[str]:
    """Use yt-dlp's ytsearch to fetch top-N video URLs for a topic."""
    if not shutil.which("yt-dlp"):
        raise ResearchError(
            "yt-dlp not on PATH. Install with `pip install yt-dlp`."
        )
    query = f"ytsearch{int(n)}:{topic}"
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s",
        "--no-warnings",
        query,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as e:
        raise ResearchError(f"yt-dlp search timed out for {topic!r}") from e
    if proc.returncode != 0:
        raise ResearchError(
            f"yt-dlp search exit {proc.returncode}: "
            f"{proc.stderr.strip().splitlines()[-1] if proc.stderr else 'no stderr'}"
        )
    ids = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return [f"https://www.youtube.com/watch?v={vid}" for vid in ids]


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------
import re

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "you", "your", "are", "but",
    "from", "have", "has", "not", "all", "any", "can", "into", "out", "what",
    "how", "why", "when", "where", "which", "who", "whose", "their", "they",
    "them", "his", "her", "its", "our", "ours", "she", "him", "his", "more",
    "most", "less", "very", "much", "some", "than", "then", "there", "here",
    "about", "would", "could", "should", "will", "shall", "may", "might",
    "must", "also", "other", "another", "such", "same", "just", "only",
    "even", "ever", "never", "always", "often", "sometimes", "usually",
    "going", "good", "bad", "well", "really", "thing", "things", "way",
    "ways", "make", "makes", "made", "get", "got", "see", "seen", "look",
    "looks", "been", "being", "want", "wants", "need", "needs", "use",
    "uses", "used", "know", "known", "show", "shows", "told", "tell",
    "let", "lets", "say", "says", "said", "your", "this",
}


def _consensus_terms(audits: list[AuditReport], top_n: int = 30
                      ) -> list[tuple[str, int]]:
    """Find terms that appear across multiple videos.

    Returns terms ranked by document-frequency (number of distinct
    videos using them, not raw occurrence count). Lowercase, stopwords
    filtered, length >= 4.
    """
    from collections import Counter
    doc_freq: Counter[str] = Counter()
    for r in audits:
        # Token the cleaned transcript; dedup per-doc to get DF, not TF.
        toks = set(re.findall(r"[a-z]{4,}", r.transcript.text.lower()))
        toks -= _STOPWORDS
        for t in toks:
            doc_freq[t] += 1
    # Only terms in >= 2 documents are "consensus"; otherwise it's just
    # one creator's vocabulary.
    return [(t, n) for t, n in doc_freq.most_common(top_n) if n >= 2]


# ---------------------------------------------------------------------------
# Top-level research()
# ---------------------------------------------------------------------------
def research(
    topic: str,
    *,
    n: int = 5,
    domain: str = "general",
    vetter=None,
    max_consensus_terms: int = 30,
) -> ResearchReport:
    """Find N videos on `topic`, audit each, synthesize a report.

    Args:
        topic: the topic to research (e.g. "intermittent fasting science",
               "time-series momentum strategies").
        n: number of top YouTube results to audit. 3-10 is typical.
        domain: hint for the per-video vetter.
        vetter: optional Vetter implementation passed through to audit().
        max_consensus_terms: cap the consensus-terms table.

    Raises:
        ResearchError: on YouTube search failure.

    Returns: a populated `ResearchReport`. Use `.to_markdown()` to render.
    """
    urls = _search_youtube(topic, n)
    audits: list[AuditReport] = []
    failures: list[dict] = []
    for url in urls:
        try:
            audits.append(audit(url, domain=domain, vetter=vetter))
        except FetchError as e:
            failures.append({"url": url, "error": str(e)})
    high_evidence = [a for a in audits if a.verdict == "HIGH_EVIDENCE"]
    consensus = _consensus_terms(audits, top_n=max_consensus_terms)
    return ResearchReport(
        topic=topic,
        domain=domain,
        audits=audits,
        failures=failures,
        consensus_terms=consensus,
        high_evidence_audits=high_evidence,
    )
