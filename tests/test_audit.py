"""Tests for receipts.audit — claim extraction + evidence scoring + reporting."""
from receipts.audit import (
    AuditReport, Claim, SkeletonVetter, _split_sentences,
    _NUMBER_RE, _SOURCE_RE, _TESTABLE_RE,
)
from receipts.fetcher import VideoMetadata
from receipts.transcript import Transcript


def _meta() -> VideoMetadata:
    return VideoMetadata(
        video_id="abc",
        url="https://youtu.be/abc",
        title="Test Video",
        channel="Test Ch",
        upload_date="20240101",
        duration_seconds=600,
        view_count=1000,
        like_count=10,
        description="",
    )


# ---- regex sanity ----
def test_number_re_catches_quantitative():
    assert _NUMBER_RE.search("up 5% in the last week")
    assert _NUMBER_RE.search("trades at 2x leverage")
    assert _NUMBER_RE.search("avg loss $1,500")
    assert not _NUMBER_RE.search("trades a lot")


def test_source_re_catches_sourced_claims():
    assert _SOURCE_RE.search("according to a 2019 study")
    assert _SOURCE_RE.search("backtested over the last 5 years")
    assert _SOURCE_RE.search("with n = 42 trades")
    assert _SOURCE_RE.search("Sharpe of 2.1")
    assert not _SOURCE_RE.search("I think this works")


def test_testable_re_catches_conditionals():
    assert _TESTABLE_RE.search("when price breaks resistance, enter long")
    assert _TESTABLE_RE.search("the rule is to buy on red")
    assert _TESTABLE_RE.search("if it dips below sma50")


# ---- sentence splitter ----
def test_split_sentences_basic():
    s = ("The market always goes up. When you buy low, sell high. "
         "Pretty simple stuff.")
    parts = _split_sentences(s)
    assert len(parts) >= 2


def test_split_sentences_drops_short():
    s = "Hi. This is a longer sentence with enough content to keep it."
    parts = _split_sentences(s)
    # "Hi." should be dropped (< 20 chars).
    assert all(len(p) > 20 for p in parts)


# ---- SkeletonVetter ----
def test_skeleton_vetter_extracts_testable_claims():
    t = Transcript(
        text=(
            "When price breaks resistance, you should enter long with stop "
            "below the swing low. According to a study with n = 200 trades, "
            "the win rate was 65%. The market never lies if you wait for "
            "the right setup."
        ),
        cues=[],
    )
    v = SkeletonVetter()
    r = v.vet(_meta(), t, domain="trading")
    assert isinstance(r, AuditReport)
    assert len(r.claims) >= 2
    # At least one claim should have all three flags.
    high = [c for c in r.claims if c.evidence_score >= 2]
    assert len(high) >= 1


def test_skeleton_vetter_unsupported_for_pure_vibes():
    t = Transcript(
        text=("If you believe in the trade, the market will reward you. "
              "When you trust your gut, you'll always do well in the long "
              "run because the market eventually confirms what you knew."),
        cues=[],
    )
    v = SkeletonVetter()
    r = v.vet(_meta(), t, domain="general")
    # Vibes-only transcript -> low or unsupported verdict.
    assert r.verdict in ("LOW_EVIDENCE", "UNSUPPORTED")


def test_skeleton_vetter_caps_at_max_claims():
    # Build a transcript with 50 testable sentences.
    lines = ["When the price moves above the level, enter long with "
             "stop below the swing." for _ in range(50)]
    t = Transcript(text=" ".join(lines), cues=[])
    v = SkeletonVetter(max_claims=10)
    r = v.vet(_meta(), t, domain="trading")
    assert len(r.claims) <= 10


# ---- AuditReport rendering ----
def test_to_markdown_minimal():
    r = AuditReport(metadata=_meta(),
                    transcript=Transcript(text="hello world", cues=[]))
    md = r.to_markdown()
    assert "# Audit: Test Video" in md
    assert "Test Ch" in md
    assert "https://youtu.be/abc" in md
    assert "## Transcript" in md
    assert "hello world" in md


def test_to_markdown_with_claims():
    c = Claim(text="When X, do Y with stop at Z.",
              has_number=True, has_source=False, is_testable=True)
    r = AuditReport(metadata=_meta(),
                    transcript=Transcript(text="x", cues=[]),
                    claims=[c],
                    verdict="MIXED")
    md = r.to_markdown()
    assert "MIXED" in md
    assert "When X, do Y" in md
    assert "2/3" in md   # evidence_score


def test_claim_evidence_score_sums_flags():
    assert Claim("x", True, True, True).evidence_score == 3
    assert Claim("x", True, False, True).evidence_score == 2
    assert Claim("x", False, False, False).evidence_score == 0
