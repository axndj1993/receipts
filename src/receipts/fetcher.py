"""Fetch YouTube video metadata + transcript via yt-dlp."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class FetchError(Exception):
    """Raised when yt-dlp fails or the video has no usable subtitles."""


@dataclass
class VideoMetadata:
    """Subset of yt-dlp's info-json that receipts uses downstream.

    Pure data; the audit pipeline writes nothing back here.
    """
    video_id: str
    url: str
    title: str
    channel: str
    upload_date: str            # YYYYMMDD as yt-dlp emits it
    duration_seconds: int
    view_count: int | None
    like_count: int | None
    description: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    chapters: list[dict] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def duration_pretty(self) -> str:
        """Human-readable duration: '8m 10s', '1h 23m'."""
        h, rem = divmod(self.duration_seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    @classmethod
    def from_info_json(cls, info: dict[str, Any], url: str) -> "VideoMetadata":
        return cls(
            video_id=info.get("id", ""),
            url=url,
            title=info.get("title", "(untitled)"),
            channel=info.get("uploader") or info.get("channel", "(unknown)"),
            upload_date=info.get("upload_date", ""),
            duration_seconds=int(info.get("duration", 0) or 0),
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            description=info.get("description", "") or "",
            categories=list(info.get("categories") or []),
            tags=list(info.get("tags") or []),
            chapters=list(info.get("chapters") or []),
            raw=info,
        )


def _yt_dlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def fetch_video(
    url: str,
    *,
    workdir: Path | str | None = None,
    sub_lang: str = "en",
    keep_files: bool = False,
) -> tuple[VideoMetadata, str]:
    """Fetch metadata + raw VTT subtitles for a YouTube URL.

    Returns: (VideoMetadata, raw_vtt_text)

    Args:
        url: YouTube URL or `youtu.be` short link.
        workdir: where yt-dlp writes its tmp files (default: a fresh
            subdir under the system temp).
        sub_lang: subtitle language preference (yt-dlp `--sub-lang`).
        keep_files: if True, leaves the .info.json + .vtt on disk for
            debugging. Default False (cleans up on success).

    Raises:
        FetchError: if yt-dlp is missing, the network call fails, or
            the video has no captions in `sub_lang`.
    """
    if not _yt_dlp_available():
        raise FetchError(
            "yt-dlp not found on PATH. Install with `pip install yt-dlp`."
        )

    if workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix="receipts_"))
    else:
        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

    out_template = str(workdir / "yt_%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--write-info-json",
        "--sub-lang", sub_lang,
        "--sub-format", "vtt",
        "-o", out_template,
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"yt-dlp timed out after 180s for {url}") from e
    if proc.returncode != 0:
        raise FetchError(
            f"yt-dlp exit {proc.returncode}: {proc.stderr.strip().splitlines()[-1] if proc.stderr else 'no stderr'}"
        )

    info_files = list(workdir.glob("yt_*.info.json"))
    if not info_files:
        raise FetchError(f"yt-dlp produced no info.json in {workdir}")
    info_path = info_files[0]
    info = json.loads(info_path.read_text(encoding="utf-8"))
    meta = VideoMetadata.from_info_json(info, url=url)

    vtt_files = list(workdir.glob(f"yt_*.{sub_lang}.vtt"))
    if not vtt_files:
        raise FetchError(
            f"no {sub_lang} subtitles found for {url} — video may have "
            f"captions disabled or only manual non-{sub_lang} captions."
        )
    raw_vtt = vtt_files[0].read_text(encoding="utf-8")

    if not keep_files:
        for f in workdir.glob("yt_*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            workdir.rmdir()
        except OSError:
            pass

    return meta, raw_vtt
