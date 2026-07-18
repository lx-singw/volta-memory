"use client";

import { useEffect, useState } from "react";
import MemoryGraph from "../components/MemoryGraph";
import { BrainCircuit } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ENTITY_ID = process.env.NEXT_PUBLIC_DEMO_ENTITY_ID || "demo-consumer-1";
const ENABLED = process.env.NEXT_PUBLIC_ENABLE_TRANSPARENCY_VIEW !== "false";

export default function MemoryPage() {
  const [memories, setMemories] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ENABLED) return;
    fetch(`${API_BASE}/entities/${ENTITY_ID}/memories`)
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json();
      })
      .then((data) => setMemories(data.memories || []))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load memories"));
  }, []);

  if (!ENABLED) {
    return <div style={{ padding: "1.5rem", background: "#020617", color: "#f8fafc", minHeight: "100vh" }}>Memory transparency view is disabled.</div>;
  }

  return (
    <div style={{ padding: "2rem", background: "#020617", color: "#f8fafc", minHeight: "100vh", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "0.5rem" }}>
        <BrainCircuit size={32} color="#facc15" />
        <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: 600 }}>Neural Memory Matrix</h1>
      </div>
      <p style={{ color: "#94a3b8", marginBottom: "2rem", fontSize: "1.1rem" }}>
        Live visualization of core memory structures for entity: <span style={{ color: "#38bdf8" }}>{ENTITY_ID}</span>
      </p>
      
      {error && (
        <div style={{ background: "rgba(248, 113, 113, 0.1)", color: "#f87171", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(248, 113, 113, 0.3)", marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      
      <MemoryGraph memories={memories} />
    </div>
  );
}
