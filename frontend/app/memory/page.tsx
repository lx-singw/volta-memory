"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, BrainCircuit, History, RefreshCcw, ShieldCheck } from "lucide-react";
import MemoryGraph from "../components/MemoryGraph";
import { getRuntimeConfig, type MemoryDTO, type MemoryRelation, VoltaApi } from "../lib/api";

export default function MemoryPage() {
  const [api, setApi] = useState<VoltaApi | null>(null);
  const [memories, setMemories] = useState<MemoryDTO[]>([]);
  const [timeline, setTimeline] = useState<MemoryDTO[]>([]);
  const [relationships, setRelationships] = useState<MemoryRelation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [focusMemoryId, setFocusMemoryId] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setFocusMemoryId(params.get("focus"));
    void getRuntimeConfig().then((config) => setApi(new VoltaApi(config)));
  }, []);

  const loadMemories = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    setError(null);
    try {
      const [memoryResult, timelineResult] = await Promise.allSettled([api.getMemories(), api.getTimeline()]);
      if (memoryResult.status === "rejected") throw memoryResult.reason;
      setMemories(memoryResult.value.memories);
      setRelationships(memoryResult.value.relationships);
      setTimeline(timelineResult.status === "fulfilled" && timelineResult.value.length ? timelineResult.value : memoryResult.value.memories);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Volta could not load memory evidence.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { void loadMemories(); }, [loadMemories]);

  const current = memories.filter((memory) => memory.status === "eligible").length;
  const retained = memories.filter((memory) => memory.status === "retained").length;
  const excluded = memories.filter((memory) => memory.status === "excluded").length;

  return <div className="page-wrap memory-page">
    <section className="memory-hero">
      <div><p className="eyebrow">Evidence, not assumptions</p><h1 className="display">Volta Memory Map</h1><p>A live evidence map showing what Volta knows, what changed, and what it is no longer using.</p></div>
      {!loading && !error ? <div className="memory-metrics" aria-label="Memory totals"><div><strong>{memories.length}</strong><span>Total memories</span></div><div><strong>{current}</strong><span>Current</span></div><div><strong>{retained}</strong><span>Retained</span></div><div><strong>{excluded}</strong><span>Excluded</span></div></div> : null}
    </section>

    {loading ? <div className="memory-skeleton" aria-label="Loading memory evidence" aria-busy="true"><div className="skeleton-line short" /><div className="skeleton-block" /><span className="sr-only">Loading verified memory evidence</span></div> : null}

    {!loading && error ? <section className="panel memory-error" role="alert"><span className="icon-box large"><AlertTriangle size={24} /></span><div><p className="eyebrow">Memory unavailable</p><h2>Volta could not verify the stored context</h2><p>Nothing is reported as empty because the request did not complete. Check the memory service, then try again.</p></div><button type="button" className="button button-primary" onClick={() => void loadMemories()}><RefreshCcw size={16} /> Retry</button></section> : null}

    {!loading && !error ? <>
      <section className="memory-principles"><div><ShieldCheck size={18} /><span><strong>Current evidence</strong> may guide advice.</span></div><div><History size={18} /><span><strong>Retained evidence</strong> stays visible for accountability.</span></div></section>
      {memories.length === 0 ? <section className="panel graph-empty"><span className="icon-box large"><BrainCircuit size={24} /></span><h2>No memories stored yet</h2><p>Complete a consultation to extract confirmed observations. Volta will not invent context to fill this space.</p><Link className="button button-primary" href="/try">Start a private consultation <ArrowRight size={16} /></Link></section> : <MemoryGraph memories={timeline.length ? timeline : memories} relationships={relationships} focusMemoryId={focusMemoryId} />}
    </> : null}
  </div>;
}
