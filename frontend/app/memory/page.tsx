"use client";

import { useEffect, useState } from "react";
import MemoryTable from "../components/MemoryTable";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ENTITY_ID = process.env.NEXT_PUBLIC_DEMO_ENTITY_ID || "demo-consumer-1";
const ENABLED = process.env.NEXT_PUBLIC_ENABLE_TRANSPARENCY_VIEW !== "false";

export default function MemoryPage() {
  const [memories, setMemories] = useState<unknown[]>([]);
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
    return <p style={{ padding: "1.5rem" }}>Memory transparency view is disabled.</p>;
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <h1>Memory transparency</h1>
      <p style={{ color: "#94a3b8" }}>Read-only view of stored memories for {ENTITY_ID}</p>
      {error && <p style={{ color: "#f87171" }}>{error}</p>}
      <MemoryTable memories={memories as Record<string, unknown>[]} />
    </div>
  );
}
