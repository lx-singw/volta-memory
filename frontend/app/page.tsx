"use client";

import { useState } from "react";
import ChatMessage from "./components/ChatMessage";
import SessionControls from "./components/SessionControls";

type ChatEntry = { role: "user" | "assistant"; content: string; memoryContext?: unknown[] };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ENTITY_ID = process.env.NEXT_PUBLIC_DEMO_ENTITY_ID || "demo-consumer-1";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startSession() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/sessions?entity_id=${ENTITY_ID}`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage() {
    if (!sessionId || !input.trim()) return;
    setLoading(true);
    setError(null);
    const userText = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);

    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply, memoryContext: data.memory_context_used },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  }

  async function endSession() {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/end`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      setSessionId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to end session");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "1.5rem" }}>
      <h1>Chat with Volta</h1>
      <p style={{ color: "#94a3b8" }}>Entity: {ENTITY_ID}</p>
      <SessionControls
        sessionActive={!!sessionId}
        loading={loading}
        onStart={startSession}
        onEnd={endSession}
      />
      {error && <p style={{ color: "#f87171" }}>{error}</p>}
      <div style={{ marginTop: "1rem", minHeight: 320 }}>
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} role={msg.role} content={msg.content} memoryContext={msg.memoryContext} />
        ))}
      </div>
      <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask Volta about solar for your home..."
          disabled={!sessionId || loading}
          style={{ flex: 1, padding: "0.75rem", borderRadius: 8, border: "1px solid #334155", background: "#1e293b", color: "#e2e8f0" }}
        />
        <button onClick={sendMessage} disabled={!sessionId || loading} style={buttonStyle}>
          Send
        </button>
      </div>
    </div>
  );
}

const buttonStyle: React.CSSProperties = {
  padding: "0.75rem 1rem",
  borderRadius: 8,
  border: "none",
  background: "#2563eb",
  color: "white",
  cursor: "pointer",
};
