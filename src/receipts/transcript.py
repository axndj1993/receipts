"""Parse yt-dlp's auto-generated VTT into a clean transcript."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Transcript:
    """A cleaned transcript, with both the flat text and the original
    per-cue timestamps (for citing 'around 3:14 they say...')."""
    text: str
    cues: list[tuple[float, str]]   # (start_seconds, text)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def excerpt(self, n_chars: int = 800) -> str:
        """First n_chars characters; useful for headers."""
        if len(self.text) <= n_chars:
            return self.text
        cut = self.text[:n_chars]
        return cut.rsplit(" ", 1)[0] + "..."


_TIMING_LINE = re.compile(r"\d\d:\d\d:\d\d\.\d+\s+-->\s+\d\d:\d\d:\d\d\.\d+")
_INLINE_TIMING_TAG = re.compile(r"<\d\d:\d\d:\d\d\.\d+>|</?c[^>]*>")
_HMS = re.compile(r"^(\d\d):(\d\d):(\d\d)\.(\d+)")


def _parse_hms(s: str) -> float | None:
    m = _HMS.match(s)
    if not m:
        return None
    h, mn, sec, frac = m.groups()
    return int(h) * 3600 + int(mn) * 60 + int(sec) + int(frac.ljust(3, "0")[:3]) / 1000


def clean_vtt(raw: str) -> Transcript:
    """Strip VTT headers + timing lines + inline tags, dedup repeated lines.

    YouTube auto-captions repeat each phrase several times across cues
    as new words come in. This produces a clean linear transcript.
    """
    lines = raw.splitlines()
    cues: list[tuple[float, str]] = []
    current_start: float | None = None
    seen: list[str] = []

    for ln in lines:
        ln_stripped = ln.strip()
        if not ln_stripped:
            current_start = None
            continue
        if ln_stripped == "WEBVTT":
            continue
        if ln_stripped.startswith("Kind:") or ln_stripped.startswith("Language:"):
            continue
        if "-->" in ln_stripped:
            # 00:00:01.000 --> 00:00:03.000 ...
            head = ln_stripped.split("-->")[0].strip()
            current_start = _parse_hms(head)
            continue
        if re.fullmatch(r"\d+", ln_stripped):
            continue
        # Strip inline timing tags like <00:00:01.000> and <c> ... </c>
        cleaned = _INLINE_TIMING_TAG.sub("", ln_stripped).strip()
        if not cleaned:
            continue
        if seen and seen[-1] == cleaned:
            continue
        seen.append(cleaned)
        if current_start is not None:
            cues.append((current_start, cleaned))

    flat = " ".join(seen)
    return Transcript(text=flat, cues=cues)
