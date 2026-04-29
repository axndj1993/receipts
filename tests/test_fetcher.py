"""Tests for receipts.fetcher — yt-dlp wrapper + VideoMetadata."""
from receipts.fetcher import VideoMetadata


def test_video_metadata_from_info_json():
    info = {
        "id": "abc123",
        "title": "Hello",
        "uploader": "Channel A",
        "upload_date": "20240501",
        "duration": 4321,
        "view_count": 9999,
        "like_count": 100,
        "description": "test desc",
        "categories": ["Education"],
        "tags": ["a", "b"],
        "chapters": [{"title": "intro", "start_time": 0}],
    }
    m = VideoMetadata.from_info_json(info, url="https://example/abc123")
    assert m.video_id == "abc123"
    assert m.title == "Hello"
    assert m.channel == "Channel A"
    assert m.duration_seconds == 4321
    assert m.upload_date == "20240501"
    assert m.tags == ["a", "b"]
    assert m.chapters == [{"title": "intro", "start_time": 0}]


def test_video_metadata_falls_back_to_channel_field():
    info = {"id": "x", "channel": "BackupCh"}
    m = VideoMetadata.from_info_json(info, url="u")
    assert m.channel == "BackupCh"


def test_video_metadata_defaults_for_missing_fields():
    m = VideoMetadata.from_info_json({"id": "x"}, url="u")
    assert m.title == "(untitled)"
    assert m.channel == "(unknown)"
    assert m.duration_seconds == 0
    assert m.view_count is None
    assert m.like_count is None
    assert m.tags == []


def test_duration_pretty_seconds():
    m = VideoMetadata.from_info_json({"id": "x", "duration": 30}, url="u")
    assert m.duration_pretty == "30s"


def test_duration_pretty_minutes():
    m = VideoMetadata.from_info_json({"id": "x", "duration": 125}, url="u")
    assert m.duration_pretty == "2m 5s"


def test_duration_pretty_hours():
    m = VideoMetadata.from_info_json({"id": "x", "duration": 3700}, url="u")
    assert m.duration_pretty == "1h 1m"
