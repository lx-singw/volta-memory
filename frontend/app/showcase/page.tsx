"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, History, LockKeyhole, RefreshCcw, ShieldCheck } from "lucide-react";
import MemoryGraph from "../components/MemoryGraph";
import { getRuntimeConfig, type MemoryDTO, type MemoryRelation, VoltaApi } from "../lib/api";

export default function ShowcasePage() {
  const [api, setApi] = useState<VoltaApi | null>(null);
  const [memories, setMemories] = useState<MemoryDTO[]>([]);
  const [timeline, setTimeline] = useState<MemoryDTO[]>([]);
  const [relationships, setRelationships] = useState<MemoryRelation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { void getRuntimeConfig().then((config) => setApi(new VoltaApi(config))); }, []);
  const load = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    setError(null);
    try {
      const [memoryResult, timelineResult] = await Promise.all([api.getShowcaseMemories(), api.getShowcaseTimeline().catch(() => [])]);
      setMemories(memoryResult.memories);
      setRelationships(memoryResult.relationships);
      setTimeline(timelineResult.length ? timelineResult : memoryResult.memories);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Volta could not load the public showcase.");
    } finally {
      setLoading(false);
    }
  }, [api]);
  useEffect(() => { void load(); }, [load]);

  const current = memories.filter((memory) => memory.status === "eligible").length;
  const retained = memories.filter((memory) => memory.status === "retained").length;

  return <div className="page-wrap showcase-page">
    <section className="showcase-hero">
      <div><p className="eyebrow">Judge showcase</p><h1 className="display">A correction that stays accountable.</h1><p>See a real memory lifecycle: a homeowner corrects a monthly bill, Volta retains the original evidence, and only the current fact can guide later advice.</p><div className="showcase-actions"><Link className="button button-primary" href="/try">Try a private workspace <ArrowRight size={16} /></Link><span className="showcase-lock"><LockKeyhole size={15} /> Read-only seeded showcase</span></div></div>
      {!loading && !error ? <div className="showcase-proof"><span><ShieldCheck size={20} /></span><strong>{current} current facts</strong><strong>{retained} retained for audit</strong><p>Nothing here can be changed by a visitor.</p></div> : null}
    </section>

    {loading ? <div className="memory-skeleton" aria-label="Loading showcase evidence" aria-busy="true"><div className="skeleton-line short" /><div className="skeleton-block" /></div> : null}
    {!loading && error ? <section className="panel memory-error" role="alert"><span className="icon-box large"><AlertTriangle size={24} /></span><div><p className="eyebrow">Showcase unavailable</p><h2>Volta could not verify the public evidence</h2><p>Try again once the public memory service is available.</p></div><button type="button" className="button button-primary" onClick={() => void load()}><RefreshCcw size={16} /> Retry</button></section> : null}
    {!loading && !error && memories.length ? <><section className="memory-principles"><div><ShieldCheck size={18} /><span><strong>Current evidence</strong> may guide advice.</span></div><div><History size={18} /><span><strong>Earlier evidence</strong> stays visible for accountability.</span></div></section><MemoryGraph memories={timeline.length ? timeline : memories} relationships={relationships} readOnly /></> : null}
  </div>;
}
