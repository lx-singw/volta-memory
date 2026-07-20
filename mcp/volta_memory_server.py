"""Read-only Model Context Protocol server for offline Volta inspection.

It is not part of the browser/API deployment path.  Durable memory mutation is
intentionally unavailable here: public product writes must use the verified,
idempotent end-session lifecycle in the FastAPI service.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Setup PYTHONPATH dynamically so it can import app modules
mcp_dir = Path(__file__).resolve().parent
repo_root = mcp_dir.parent
backend_path = repo_root / "backend"
sys.path.append(str(backend_path))

# Load dotenv before importing app code
from dotenv import load_dotenv
load_dotenv(dotenv_path=repo_root / ".env")

from app.memory.store import list_memories
from app.memory.retrieval import build_memory_context
from app.memory.clarification import compute_dialogue_action


def log_debug(msg: str) -> None:
    # Print to stderr since stdout is reserved for JSON-RPC 2.0 communication
    sys.stderr.write(f"[DEBUG] {msg}\n")
    sys.stderr.flush()


def handle_initialize(request_id: int | str, params: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "serverInfo": {
                "name": "volta-memory-server",
                "version": "1.0.0"
            }
        }
    }


def handle_tools_list(request_id: int | str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": [
                {
                    "name": "get_memory_context",
                    "description": "Retrieve token-budgeted memory context for a user entity, ranked by decay and importance.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entity_id": {"type": "string", "description": "The unique ID of the user"},
                            "query": {"type": "string", "description": "Search query contextualized by user prompt"}
                        },
                        "required": ["entity_id", "query"]
                    }
                },
                {
                    "name": "check_memory_confidence",
                    "description": "Check confidence and recommended action (CLARIFY, STATE, SOFT_CHECK) for a given topic or memory observation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entity_id": {"type": "string", "description": "The unique ID of the user"},
                            "topic": {"type": "string", "description": "The topic or observation check target"}
                        },
                        "required": ["entity_id", "topic"]
                    }
                }
            ]
        }
    }


def handle_tools_call(request_id: int | str, params: dict) -> dict:
    name = params.get("name")
    args = params.get("arguments", {})
    entity_id = args.get("entity_id")

    if not entity_id:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32602, "message": "Missing required argument 'entity_id'"}
        }

    try:
        if name == "get_memory_context":
            query = args.get("query", "")
            memories = list_memories(entity_id, include_superseded=False)
            context = build_memory_context(entity_id, memories, query_context=query)
            
            # Format output
            lines = []
            for item in context.packed_memories:
                lines.append(f"- {item.memory.observation} (action: {item.dialogue_action})")
            
            result_text = "\n".join(lines) if lines else "No relevant memories found."
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": False
                }
            }

        elif name == "check_memory_confidence":
            topic = args.get("topic", "").lower()
            memories = list_memories(entity_id, include_superseded=False)
            
            # Find best match topic
            matched_action = "SOFT_CHECK"
            for m in memories:
                if topic in m.observation.lower():
                    # Calculate current decay confidence
                    from datetime import datetime, timezone
                    from app.memory.decay import apply_decay
                    eff = apply_decay(m, now=datetime.now(timezone.utc))
                    matched_action = compute_dialogue_action(m, eff)
                    break

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"Recommended action for '{topic}': {matched_action}"}],
                    "isError": False
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Tool '{name}' not found"}
            }

    except Exception as e:
        log_debug(f"Error executing tool {name}: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": f"Internal tool execution error: {e}"}
        }


def handle_resources_list(request_id: int | str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "resources": []
        }
    }


def handle_resources_read(request_id: int | str, params: dict) -> dict:
    uri = params.get("uri", "")
    # Expect: memory://entity/{entity_id}/summary
    if not uri.startswith("memory://entity/") or not uri.endswith("/summary"):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32602, "message": "Invalid resource URI format"}
        }

    entity_id = uri.split("/")[3]
    try:
        memories = list_memories(entity_id, include_superseded=False)
        summary = "\n".join(f"- [{m.memory_type.value}] {m.observation}" for m in memories)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": summary or "No active memories found."
                    }
                ]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": f"Failed to read resource: {e}"}
        }


def main() -> None:
    log_debug("Volta Memory MCP Server started over stdio.")
    
    for line in sys.stdin:
        line_str = line.strip()
        if not line_str:
            continue
            
        try:
            request = json.loads(line_str)
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})
            
            log_debug(f"Received JSON-RPC request: method={method}")
            
            if method == "initialize":
                response = handle_initialize(request_id, params)
            elif method == "tools/list":
                response = handle_tools_list(request_id)
            elif method == "tools/call":
                response = handle_tools_call(request_id, params)
            elif method == "resources/list":
                response = handle_resources_list(request_id)
            elif method == "resources/read":
                response = handle_resources_read(request_id, params)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method '{method}' not found"}
                }
                
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error: Invalid JSON"}
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            log_debug(f"Unhandled server error: {e}")


if __name__ == "__main__":
    main()
