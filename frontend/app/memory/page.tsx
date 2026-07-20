"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, BrainCircuit, History, RefreshCcw, ShieldCheck } from "lucide-react";
import MemoryGraph from "../components/MemoryGraph";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ENTITY_ID = process.env.NEXT_PUBLIC_DEMO_ENTITY_ID || "demo-consumer-1";
const ENABLED = process.env.NEXT_PUBLIC_ENABLE_TRANSPARENCY_VIEW !== "false";

export default function MemoryPage() {
  const [memories, setMemories] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(ENABLED);
  const [loaded, setLoaded] = useState(false);

  const loadMemories = useCallback(async () => {
    setLoading(true);
    setError(null);
    setLoaded(false);
    try {
      const response = await fetch(`${API_BASE}/entities/${ENTITY_ID}/memories`);
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      setMemories(Array.isArray(data.memories) ? data.memories : []);
      setLoaded(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Volta could not load memory evidence.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ENABLED) void loadMemories();
  }, [loadMemories]);

  if (!ENABLED) return <div className="page-wrap"><div className="panel disabled-view"><BrainCircuit size={24} /><h1>Memory transparency is disabled</h1><p>This view is not available in the current environment.</p></div></div>;

  const active = memories.filter((memory) => !memory.is_superseded).length;
  const superseded = memories.length - active;

  return <div className="page-wrap memory-page">
    <section className="memory-hero">
      <div><p className="eyebrow">Evidence, not assumptions</p><h1 className="display">Volta Memory Map</h1><p>A live evidence map showing what Volta knows, what changed, and what it is no longer using.</p></div>
      {loaded && <div className="memory-metrics" aria-label="Memory totals"><div><strong>{memories.length}</strong><span>Total memories</span></div><div><strong>{active}</strong><span>Current</span></div><div><strong>{superseded}</strong><span>Superseded</span></div></div>}
    </section>

    {loading && <div className="memory-skeleton" aria-label="Loading memory evidence" aria-busy="true"><div className="skeleton-line short" /><div className="skeleton-block" /><span className="sr-only">Loading this homeowner&apos;s memory evidence</span></div>}

    {!loading && error && <section className="panel memory-error" role="alert"><span className="icon-box large"><AlertTriangle size={24} /></span><div><p className="eyebrow">Memory unavailable</p><h2>Volta could not verify the stored context</h2><p>Nothing is being reported as empty because the request did not complete. Check the memory service, then try again.</p><details><summary>Technical detail</summary><code>{error}</code></details></div><button className="button button-primary" onClick={() => void loadMemories()}><RefreshCcw size={16} /> Retry</button></section>}

    {!loading && loaded && <>
      <section className="memory-principles"><div><ShieldCheck size={18} /><span><strong>Current evidence</strong> remains available to advice.</span></div><div><History size={18} /><span><strong>Superseded evidence</strong> stays visible for accountability.</span></div></section>
      {memories.length === 0 ? <section className="panel graph-empty"><span className="icon-box large"><BrainCircuit size={24} /></span><h2>No memories stored yet</h2><p>Complete a consultation to extract confirmed observations. Volta will not invent context to fill this space.</p><Link className="button button-primary" href="/">Start a consultation <ArrowRight size={16} /></Link></section> : <MemoryGraph memories={memories} />}
    </>}
  </div>;
}
