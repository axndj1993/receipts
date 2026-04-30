"""Tests for receipts.install — auto-writing MCP config into AI hosts."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from receipts import install as _install


def test_clients_table_covers_expected_hosts():
    assert set(_install.CLIENTS) == {
        "claude-code", "cursor", "cline", "codex", "continue", "zed",
    }


def test_install_claude_code_uses_dot_mcp_json_at_repo_root(tmp_path,
                                                             monkeypatch):
    """Project-scope Claude Code config MUST be `.mcp.json` at repo root.
    `.claude/mcp.json` is silently ignored by Claude Code — guard the
    common-mistake doc bug at the install layer."""
    monkeypatch.chdir(tmp_path)
    # Recompute paths after cwd swap (CLIENTS table was built at import
    # time in the test process's original cwd).
    spec = _install._ClientSpec(
        name="Claude Code",
        config_paths=_install._claude_code_paths(),
        format="json",
        servers_key_path=["mcpServers"],
    )
    assert spec.config_paths == [tmp_path / ".mcp.json"]
    assert all(".claude/mcp.json" not in str(p) for p in spec.config_paths)


def test_install_writes_minimal_block(tmp_path):
    target = tmp_path / ".mcp.json"
    written = _install.install("claude-code", config_path=target)
    assert written == target
    data = json.loads(target.read_text())
    assert data == {
        "mcpServers": {
            "receipts": {"command": "receipts-mcp"},
        },
    }


def test_install_preserves_existing_servers(tmp_path):
    target = tmp_path / ".mcp.json"
    target.write_text(json.dumps({
        "mcpServers": {
            "tether": {
                "command": "tether-mcp",
                "env": {"TETHER_PROFILE": "futures-bot"},
            }
        }
    }))
    _install.install("claude-code", config_path=target)
    data = json.loads(target.read_text())
    assert "tether" in data["mcpServers"]
    assert data["mcpServers"]["tether"]["command"] == "tether-mcp"
    assert data["mcpServers"]["tether"]["env"] == {
        "TETHER_PROFILE": "futures-bot"}
    assert data["mcpServers"]["receipts"] == {"command": "receipts-mcp"}


def test_install_is_idempotent(tmp_path):
    target = tmp_path / ".mcp.json"
    _install.install("claude-code", config_path=target)
    first = target.read_text()
    _install.install("claude-code", config_path=target)
    second = target.read_text()
    assert first == second


def test_install_creates_parent_dir(tmp_path):
    nested = tmp_path / "nope" / "still-nope" / ".mcp.json"
    assert not nested.parent.exists()
    _install.install("claude-code", config_path=nested)
    assert nested.exists()


def test_install_unknown_client_raises():
    with pytest.raises(SystemExit):
        _install.install("emacs")


def test_install_custom_server_name(tmp_path):
    target = tmp_path / ".mcp.json"
    _install.install("claude-code", config_path=target,
                     server_name="audit-agent")
    data = json.loads(target.read_text())
    assert "audit-agent" in data["mcpServers"]
    assert "receipts" not in data["mcpServers"]


def test_install_handles_empty_existing_file(tmp_path):
    target = tmp_path / ".mcp.json"
    target.write_text("")
    _install.install("claude-code", config_path=target)
    data = json.loads(target.read_text())
    assert data == {"mcpServers": {"receipts": {"command": "receipts-mcp"}}}
