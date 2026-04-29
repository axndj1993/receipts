"""Tests for receipts.transcript — VTT parsing + cleaning."""
from receipts.transcript import Transcript, clean_vtt


SAMPLE_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.500
hello world

00:00:02.500 --> 00:00:04.000
hello world this is a test

00:00:04.000 --> 00:00:05.500
this is a test of the cleaner
"""


def test_clean_vtt_strips_headers_and_dedups():
    t = clean_vtt(SAMPLE_VTT)
    # WEBVTT, Kind:, Language: dropped; timing lines dropped;
    # contiguous duplicate "hello world" deduped.
    assert "WEBVTT" not in t.text
    assert "Kind:" not in t.text
    assert "-->" not in t.text
    # Final text should contain each unique phrase once, joined.
    assert "hello world" in t.text
    assert "this is a test" in t.text
    assert "this is a test of the cleaner" in t.text
    # Cue list captures the start times of unique cues.
    assert len(t.cues) >= 3
    assert t.cues[0][0] == 0.0
    assert t.cues[0][1] == "hello world"


def test_word_count_and_excerpt():
    t = clean_vtt(SAMPLE_VTT)
    assert t.word_count > 0
    assert len(t.excerpt(50)) <= 53   # 50 + "..."


def test_inline_timing_tags_stripped():
    vtt = """WEBVTT

00:00:00.000 --> 00:00:01.000
<00:00:00.500><c>tag</c>kept

"""
    t = clean_vtt(vtt)
    assert "<" not in t.text
    assert ">" not in t.text
    assert "kept" in t.text


def test_empty_vtt():
    t = clean_vtt("WEBVTT\n\n")
    assert t.text == ""
    assert t.cues == []
