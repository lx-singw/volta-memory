import json
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_connection

client = TestClient(app)


def test_sse_streaming_endpoint():
    # 1. Create a dummy session
    session_id = uuid4()
    entity_id = f"test-stream-{uuid4()}"
    
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (id, entity_id) VALUES (%s, %s)",
            (session_id, entity_id)
        )

    # 2. Call the message endpoint with stream=true query parameter
    # Use follow_redirects=True or similar, and check SSE output
    response = client.post(
        f"/sessions/{session_id}/messages?stream=true",
        json={"message": "I prefer solar sizing for 5kW inverter."}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # 3. Read streamed chunks
    lines = response.text.split("\n")
    data_lines = [l for l in lines if l.startswith("data:")]
    assert len(data_lines) > 0
    
    # Parse the first JSON data chunk
    first_chunk = json.loads(data_lines[0][5:])
    assert "token" in first_chunk or "error" in first_chunk
