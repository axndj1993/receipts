"""Auto-install receipts' MCP server config into AI agent hosts.

Mirrors tether's `tether install <host>` pattern so a receipts user
can wire the MCP block into Claude Code / Cursor / Cline / Codex /
Continue / Zed with one command:

    receipts install claude-code
    receipts install cursor
    receipts install cline
    receipts install codex
    receipts install continue
    receipts install zed

Receipts has no profiles, no env vars, no hooks — the install is
strictly the MCP block:

    {
      "mcpServers": {
        "receipts": {
          "command": "receipts-mcp"
        }
      }
    }

Idempotent: re-running overwrites the receipts entry without
disturbing other servers in the same config.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Per-host config locations
# ---------------------------------------------------------------------------
class _ClientSpec:
    def __init__(
        self,
        name: str,
        config_paths: list[Path],
        format: str,                       # "json" | "yaml"
        servers_key_path: list[str],
    ) -> None:
        self.name = name
        self.config_paths = config_paths
        self.format = format
        self.servers_key_path = servers_key_path


def _claude_code_paths() -> list[Path]:
    # Project scope: Claude Code reads `.mcp.json` at the repo root
    # (NOT `.claude/mcp.json` — that path is silently ignored).
    # User scope lives inside `~/.claude.json` (multi-key file) and
    # is managed via `claude mcp add -s user`, not a standalone file.
    return [Path.cwd() / ".mcp.json"]


CLIENTS: dict[str, _ClientSpec] = {
    "claude-code": _ClientSpec(
        name="Claude Code",
        config_paths=_claude_code_paths(),
        format="json",
        servers_key_path=["mcpServers"],
    ),
    "cursor": _ClientSpec(
        name="Cursor",
        config_paths=[
            Path.cwd() / ".cursor" / "mcp.json",
            Path.home() / ".cursor" / "mcp.json",
        ],
        format="json",
        servers_key_path=["mcpServers"],
    ),
    "cline": _ClientSpec(
        # Cline uses VS Code's settings.json for MCP, but the location
        # varies per-OS and the schema is nested. Easiest portable
        # path: write a sidecar JSON the user can copy.
        name="Cline (sidecar)",
        config_paths=[Path.cwd() / ".cline-mcp.json"],
        format="json",
        servers_key_path=["mcpServers"],
    ),
    "codex": _ClientSpec(
        name="Codex CLI",
        config_paths=[
            Path.cwd() / ".codex" / "mcp.json",
            Path.home() / ".codex" / "mcp.json",
        ],
        format="json",
        servers_key_path=["mcpServers"],
    ),
    "continue": _ClientSpec(
        name="Continue.dev",
        config_paths=[
            Path.cwd() / ".continue" / "config.yaml",
            Path.home() / ".continue" / "config.yaml",
        ],
        format="yaml",
        servers_key_path=["mcpServers"],
    ),
    "zed": _ClientSpec(
        name="Zed (sidecar)",
        config_paths=[Path.cwd() / ".zed-mcp.json"],
        format="json",
        servers_key_path=["mcpServers"],
    ),
}


# ---------------------------------------------------------------------------
# Server-block builder
# ---------------------------------------------------------------------------
def _build_server_block() -> dict:
    """receipts-mcp takes no env or args — just the command."""
    return {"command": "receipts-mcp"}


# ---------------------------------------------------------------------------
# Read / write helpers
# ---------------------------------------------------------------------------
def _read_existing(spec: _ClientSpec, path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}
    if spec.format == "json":
        return json.loads(raw)
    if spec.format == "yaml":
        try:
            import yaml
        except ImportError:
            raise SystemExit(
                "receipts install continue: requires PyYAML. "
                "Install with: pip install pyyaml"
            )
        return yaml.safe_load(raw) or {}
    raise ValueError(f"unknown format: {spec.format}")


def _write_back(spec: _ClientSpec, path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if spec.format == "json":
        text = json.dumps(data, indent=2) + "\n"
    elif spec.format == "yaml":
        import yaml  # imported above in _read_existing path
        text = yaml.safe_dump(data, sort_keys=False)
    else:
        raise ValueError(f"unknown format: {spec.format}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Top-level install
# ---------------------------------------------------------------------------
def install(
    client: str,
    *,
    config_path: Path | None = None,
    server_name: str = "receipts",
) -> Path:
    """Install receipts' MCP server into the named client's config.

    Args:
        client: one of CLIENTS keys ("claude-code", "cursor", ...).
        config_path: explicit path to write to. If unset, picks the
            first existing one from spec.config_paths, or the first
            entry if none exist (creating it).
        server_name: key in the mcpServers dict (default "receipts").

    Returns the path written.
    """
    if client not in CLIENTS:
        raise SystemExit(
            f"unknown client {client!r}. supported: "
            f"{', '.join(sorted(CLIENTS))}"
        )
    spec = CLIENTS[client]
    if config_path is None:
        existing = [p for p in spec.config_paths if p.exists()]
        config_path = existing[0] if existing else spec.config_paths[0]

    data = _read_existing(spec, config_path)
    cur = data
    for key in spec.servers_key_path[:-1]:
        cur = cur.setdefault(key, {})
    last = spec.servers_key_path[-1]
    servers = cur.setdefault(last, {})
    if not isinstance(servers, dict):
        # Continue.dev's YAML schema sometimes uses a list. Convert.
        servers = {}
        cur[last] = servers
    servers[server_name] = _build_server_block()
    _write_back(spec, config_path, data)
    return config_path
