import json
import subprocess
import sys
from pathlib import Path


def test_mcp_server_stdio():
    # Path to volta_memory_server.py
    mcp_script = Path(__file__).resolve().parent.parent.parent / "mcp" / "volta_memory_server.py"
    
    # Spawn the process
    proc = subprocess.Popen(
        [sys.executable, str(mcp_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 1. Send initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    proc.stdin.write(json.dumps(init_request) + "\n")
    proc.stdin.flush()
    
    response_line = proc.stdout.readline()
    resp = json.loads(response_line)
    
    assert resp["id"] == 1
    assert "capabilities" in resp["result"]
    assert resp["result"]["serverInfo"]["name"] == "volta-memory-server"

    # 2. Send tools/list request
    list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    proc.stdin.write(json.dumps(list_request) + "\n")
    proc.stdin.flush()
    
    response_line = proc.stdout.readline()
    resp = json.loads(response_line)
    
    assert resp["id"] == 2
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "get_memory_context" in tool_names
    assert "write_memory" in tool_names

    # Clean up process
    proc.terminate()
    proc.wait()
