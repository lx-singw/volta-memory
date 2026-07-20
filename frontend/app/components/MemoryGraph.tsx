"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { Check, Clock3, Eye, Focus, Link2, MousePointer2, Quote, ShieldCheck, Undo2 } from "lucide-react";
import type { MemoryDTO, MemoryRelation } from "../lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => <div className="graph-loading"><span className="spinner" /> Preparing memory map…</div>,
});

type Props = {
  memories: MemoryDTO[];
  relationships?: MemoryRelation[];
  focusMemoryId?: string | null;
  readOnly?: boolean;
};

type GraphNode = { id: string; name: string; val: number; color: string; confidence: number; memory: MemoryDTO; x?: number; y?: number };
type GraphLink = { source: string; target: string; relationType: MemoryRelation["relationType"]; color: string };

const colors: Record<string, string> = {
  fact: "#F6B93B",
  preference: "#9B8AFB",
  evidence: "#42D3E8",
  retained: "#667B92",
  excluded: "#F59E6B",
  reconfirmation: "#F6B93B",
};

function dateLabel(value?: string | null) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Not recorded" : new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(date);
}

function nodeKind(memory: MemoryDTO) {
  if (memory.status === "retained") return "retained";
  if (memory.status === "excluded") return "excluded";
  if (memory.status === "needs_reconfirmation") return "reconfirmation";
  if (memory.memoryType === "preference") return "preference";
  if (memory.memoryType === "fact" || memory.memoryType === "correction") return "fact";
  return "evidence";
}

function statusLabel(memory: MemoryDTO) {
  if (memory.status === "eligible") return "Current";
  if (memory.status === "needs_reconfirmation") return "Needs reconfirmation";
  if (memory.status === "retained") return "Retained for audit";
  return "Excluded from advice";
}

function statusClass(memory: MemoryDTO) {
  return memory.status === "eligible" ? "active" : memory.status === "needs_reconfirmation" ? "warning" : "inactive";
}

function persistedRelationships(memories: MemoryDTO[], supplied: MemoryRelation[]) {
  const byId = new Map(memories.map((memory) => [memory.id, memory]));
  const all = [...supplied, ...memories.flatMap((memory) => memory.relationships || [])];
  const hasPersistedPair = (sourceMemoryId: string, targetMemoryId: string) => all.some((relation) => (
    (relation.sourceMemoryId === sourceMemoryId && relation.targetMemoryId === targetMemoryId) ||
    (relation.sourceMemoryId === targetMemoryId && relation.targetMemoryId === sourceMemoryId)
  ));
  // A correction chain stored on the memory record/provenance is a persisted
  // relationship too.  Never connect active memories merely for visual effect.
  // Versioned reinforcements intentionally retain the prior record but store an
  // `reinforces` link; do not invent a second, misleading supersedes link.
  for (const memory of memories) {
    if (memory.provenance.prior?.id && byId.has(memory.provenance.prior.id) && !hasPersistedPair(memory.provenance.prior.id, memory.id)) {
      all.push({ sourceMemoryId: memory.provenance.prior.id, targetMemoryId: memory.id, relationType: "supersedes" });
    } else if (memory.supersededById && byId.has(memory.supersededById) && !hasPersistedPair(memory.id, memory.supersededById)) {
      all.push({ sourceMemoryId: memory.id, targetMemoryId: memory.supersededById, relationType: "supersedes" });
    }
  }
  const seen = new Set<string>();
  return all.filter((relation) => {
    const key = `${relation.sourceMemoryId}:${relation.targetMemoryId}:${relation.relationType}`;
    if (seen.has(key) || !byId.has(relation.sourceMemoryId) || !byId.has(relation.targetMemoryId)) return false;
    seen.add(key);
    return true;
  });
}

export default function MemoryGraph({ memories, relationships = [], focusMemoryId, readOnly = false }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 640, height: 520 });
  const [selectedId, setSelectedId] = useState<string | null>(focusMemoryId || memories.find((memory) => memory.memoryType === "correction" && memory.status === "eligible")?.id || memories.find((memory) => memory.status === "eligible")?.id || memories[0]?.id || null);
  const selected = memories.find((memory) => memory.id === selectedId) || null;

  useEffect(() => {
    if (focusMemoryId && memories.some((memory) => memory.id === focusMemoryId)) setSelectedId(focusMemoryId);
  }, [focusMemoryId, memories]);

  useEffect(() => {
    if (!selectedId || !memories.some((memory) => memory.id === selectedId)) setSelectedId(memories[0]?.id || null);
  }, [memories, selectedId]);

  useEffect(() => {
    if (!ref.current) return;
    const resize = () => {
      const width = Math.max(280, Math.floor(ref.current?.getBoundingClientRect().width || 640));
      setDimensions({ width, height: Math.max(420, Math.min(580, window.innerHeight - 280)) });
    };
    const observer = new ResizeObserver(resize);
    observer.observe(ref.current);
    resize();
    return () => observer.disconnect();
  }, []);

  const relations = useMemo(() => persistedRelationships(memories, relationships), [memories, relationships]);
  const graph = useMemo(() => {
    const nodes: GraphNode[] = memories.map((memory) => ({
      id: memory.id,
      name: memory.observation,
      val: Math.max(12, (memory.importance ?? memory.confidence) * 30),
      color: colors[nodeKind(memory)],
      confidence: memory.confidence,
      memory,
    }));
    const links: GraphLink[] = relations.map((relation) => ({
      source: relation.sourceMemoryId,
      target: relation.targetMemoryId,
      relationType: relation.relationType,
      color: relation.relationType === "supersedes" ? "rgba(246,185,59,.68)" : relation.relationType === "reinforces" ? "rgba(66,211,232,.5)" : "rgba(155,138,251,.5)",
    }));
    return { nodes, links };
  }, [memories, relations]);

  const select = (memory: MemoryDTO) => {
    setSelectedId(memory.id);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("focus", memory.id);
      window.history.replaceState({}, "", url);
    }
  };

  const selectedRelations = selected ? relations.filter((relation) => relation.sourceMemoryId === selected.id || relation.targetMemoryId === selected.id) : [];
  const relationDescription = (relation: MemoryRelation) => {
    const counterpartId = relation.sourceMemoryId === selected?.id ? relation.targetMemoryId : relation.sourceMemoryId;
    const counterpart = memories.find((memory) => memory.id === counterpartId);
    const label = relation.relationType === "supersedes"
      ? relation.sourceMemoryId === selected?.id ? "Replaced by" : "Replaces"
      : relation.relationType === "reinforces"
        ? relation.sourceMemoryId === selected?.id ? "Reconfirmed by" : "Reconfirmed from"
        : "Consolidated with";
    return { counterpart, label };
  };

  const sourceQuote = selected?.provenance.sourceVerified ? selected.provenance.sourceQuote : null;
  // The accessible audit trail reads as a lineage: original evidence first,
  // then its correction/reconfirmation, rather than a reverse activity feed.
  const timeline = [...memories].sort((a, b) => new Date(a.createdAt || a.lastConfirmedAt || 0).valueOf() - new Date(b.createdAt || b.lastConfirmedAt || 0).valueOf());

  return <div className="memory-rich-state">
    <div className="graph-layout">
      <section className="panel graph-panel" aria-label={readOnly ? "Read-only Volta showcase memory map" : "Interactive Volta memory map"}>
        <header><div><p className="eyebrow">Relationship map</p><h2>{readOnly ? "Showcase evidence" : "Homeowner evidence"}</h2></div><span className="pill"><MousePointer2 size={13} /> Select a memory</span></header>
        <div ref={ref} className="graph-canvas" aria-hidden="true">
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            graphData={graph}
            backgroundColor="#0A1728"
            nodeLabel={(node: any) => `${node.name} · ${Math.round(node.confidence * 100)}% confidence · ${statusLabel(node.memory)}`}
            nodeColor={(node: any) => node.color}
            nodeRelSize={6}
            linkColor={(link: any) => link.color}
            linkWidth={(link: any) => link.relationType === "supersedes" ? 2.5 : 1.4}
            linkDirectionalArrowLength={(link: any) => link.relationType === "supersedes" ? 5 : 0}
            onNodeClick={(node: any) => select(node.memory)}
            nodeCanvasObjectMode={() => "replace"}
            nodeCanvasObject={(node: any, context: CanvasRenderingContext2D) => {
              const isSelected = selectedId === node.memory.id;
              const radius = Math.max(12, Math.sqrt(node.val || 12) * 2.2);
              if (isSelected) {
                context.beginPath();
                context.arc(node.x || 0, node.y || 0, radius + 5, 0, 2 * Math.PI);
                context.fillStyle = "rgba(66, 211, 232, 0.25)";
                context.fill();
                context.beginPath();
                context.arc(node.x || 0, node.y || 0, radius + 2, 0, 2 * Math.PI);
                context.strokeStyle = "#42D3E8";
                context.lineWidth = 1.5;
                context.stroke();
              }
              context.beginPath();
              context.arc(node.x || 0, node.y || 0, radius, 0, 2 * Math.PI);
              context.fillStyle = node.color;
              context.fill();
              context.beginPath();
              context.arc(node.x || 0, node.y || 0, radius, 0, 2 * Math.PI);
              context.strokeStyle = "#0A1728";
              context.lineWidth = 1.5;
              context.stroke();
            }}
          />
        </div>
        <footer aria-label="Memory map legend"><span><i className="legend-dot gold" /> Current facts</span><span><i className="legend-dot violet" /> Preferences</span><span><i className="legend-dot cyan" /> Evidence</span><span><i className="legend-dot muted-dot" /> Retained for audit</span><span><Link2 size={12} /> Persisted links show corrections or reinforcements</span></footer>
      </section>

      <aside className="panel evidence-panel" aria-live="polite">
        {selected ? <>
          <div className="evidence-title"><div><p className="eyebrow">Selected memory</p><h2>{statusLabel(selected)}</h2></div><span className={`status-badge ${statusClass(selected)}`}>{selected.status === "eligible" ? <Check size={12} /> : <Eye size={12} />}{statusLabel(selected)}</span></div>
          <p className="selected-observation">{selected.observation}</p>
          {sourceQuote ? <blockquote><Quote size={15} /> “{sourceQuote}”{selected.provenance.sourceTurnIndex !== null && selected.provenance.sourceTurnIndex !== undefined ? <small> · Your turn {selected.provenance.sourceTurnIndex}</small> : null}</blockquote> : <p className="source-note">No verified verbatim source was persisted for this legacy memory. Volta will not present the stored observation as a direct quote.</p>}
          <dl><div><dt>Confidence</dt><dd>{Math.round(selected.confidence * 100)}%</dd></div><div><dt>Last confirmed</dt><dd>{dateLabel(selected.lastConfirmedAt)}</dd></div><div><dt>Type</dt><dd>{selected.memoryType}</dd></div><div><dt>Importance</dt><dd>{selected.importance === null ? "Not scored" : `${Math.round(selected.importance * 100)}%`}</dd></div></dl>
          {selectedRelations.length ? <div className="relation-list">{selectedRelations.map((relation) => {
            const description = relationDescription(relation);
            return description.counterpart ? <button type="button" key={`${relation.sourceMemoryId}-${relation.targetMemoryId}-${relation.relationType}`} className="relation-item" onClick={() => select(description.counterpart!)}><Undo2 size={14} /><span><small>{description.label}</small>{description.counterpart.observation}</span></button> : null;
          })}</div> : null}
          <p className="privacy-note"><ShieldCheck size={14} /> {selected.status === "eligible" ? "This current fact may guide advice." : "This record remains visible for accountability, not advice."}</p>
        </> : <div className="evidence-empty"><span className="icon-box"><Focus size={18} /></span><h2>Select a memory</h2><p>Inspect its status, source evidence, and correction relationship.</p></div>}
      </aside>
    </div>

    <section className="panel memory-list-panel"><header><div><p className="eyebrow">Accessible view</p><h2>Memory timeline</h2></div><span className="muted">Select any row to inspect it</span></header><div className="memory-list">{timeline.map((memory) => <button type="button" key={memory.id} className={`memory-list-item ${selectedId === memory.id ? "selected" : ""}`} onClick={() => select(memory)} aria-pressed={selectedId === memory.id}><span className={`memory-type-dot ${nodeKind(memory)}`} /><span className="memory-list-copy"><strong>{memory.observation}</strong><small><Clock3 size={12} /> {dateLabel(memory.lastConfirmedAt || memory.createdAt)} · {Math.round(memory.confidence * 100)}% confidence</small></span><span className={`status-badge ${statusClass(memory)}`}>{memory.status === "eligible" ? <Check size={12} /> : <Eye size={12} />}{statusLabel(memory)}</span></button>)}</div></section>
  </div>;
}
