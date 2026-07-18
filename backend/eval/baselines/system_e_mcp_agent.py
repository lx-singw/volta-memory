"""Baseline E — MCP Agent-directed baseline communicating with MCP server via JSON-RPC stdio."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from app.db import check_database, get_connection
from app.memory.extraction import extract_observations
from app.memory.models import MemoryType

logger = logging.getLogger(__name__)


def _send_rpc(proc: subprocess.Popen, method: str, params: dict, rpc_id: int) -> dict:
    req = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
        "params": params
    }
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    res_line = proc.stdout.readline()
    return json.loads(res_line)


def respond(entity_id: str, transcript: str, user_message: str) -> dict:
    packed: list[str] = []
    tokens_used = 0

    if check_database():
        try:
            # 1. Clear database rows for a clean run
            with get_connection() as conn:
                conn.execute("DELETE FROM memories WHERE entity_id = %s", (entity_id,))
                conn.execute("DELETE FROM conversations WHERE entity_id = %s", (entity_id,))

            # 2. Extract past transcript
            lines = [line.strip() for line in transcript.splitlines() if line.strip()]
            final_user_line = f"user: {user_message}"
            past_lines = []
            for line in lines:
                if line.lower() == final_user_line.lower():
                    break
                past_lines.append(line)
            
            past_transcript = "\n".join(past_lines)

            # 3. Spawn the MCP Server subprocess
            mcp_script = Path(__file__).resolve().parents[3] / "mcp" / "volta_memory_server.py"
            proc = subprocess.Popen(
                [sys.executable, str(mcp_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Initialize MCP
            _send_rpc(proc, "initialize", {}, 1)

            # 4. Extract and write past memories via MCP tool write_memory
            if past_transcript.strip():
                drafts = extract_observations(past_transcript)
                for i, draft in enumerate(drafts):
                    _send_rpc(
                        proc,
                        "tools/call",
                        {
                            "name": "write_memory",
                            "arguments": {
                                "entity_id": entity_id,
                                "observation": draft.observation,
                                "memory_type": draft.memory_type.value
                            }
                        },
                        10 + i
                    )

            # 5. Retrieve Context via MCP tool get_memory_context
            ret_resp = _send_rpc(
                proc,
                "tools/call",
                {
                    "name": "get_memory_context",
                    "arguments": {
                        "entity_id": entity_id,
                        "query": user_message
                    }
                },
                99
            )

            # Parse results
            result = ret_resp.get("result", {})
            content = result.get("content", [{}])[0].get("text", "")
            if content and "No memories found" not in content:
                packed = [line[2:] for line in content.splitlines() if line.startswith("- ")]
                # Strip out the bracketed dialogue action notes if present
                clean_packed = []
                for item in packed:
                    if " (action: " in item:
                        item = item.split(" (action: ")[0]
                    clean_packed.append(item)
                packed = clean_packed

            proc.terminate()
            proc.wait()

        except Exception as e:
            logger.error(f"Error in System E respond: {e}", exc_info=True)

    return {
        "reply": f"(mcp agent) {user_message}",
        "memory_context_used": [{"observation": obs} for obs in packed],
        "tokens_used": tokens_used,
        "cost_usd": 0.015,
    }
