"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { Check, Clock3, Eye, Focus, Link2, MousePointer2, Quote, ShieldCheck } from "lucide-react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false, loading: () => <div className="graph-loading"><span className="spinner" /> Preparing memory map…</div> });

type Props = { memories: any[] };
const text = (memory: any) => memory.observation || memory.content || memory.text || "Untitled memory";
const confidence = (memory: any) => memory.effective_confidence ?? memory.confidence ?? memory.base_confidence ?? 0.5;
const dateLabel = (value?: string | null) => value ? new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(new Date(value)) : "Not recorded";

function nodeKind(memory: any) {
  if (memory.is_superseded) return "superseded";
  if (memory.memory_type === "preference") return "preference";
  if (memory.memory_type === "correction" || memory.memory_type === "fact") return "fact";
  return "evidence";
}

const colors: Record<string, string> = { fact: "#F6B93B", preference: "#9B8AFB", evidence: "#42D3E8", superseded: "#667B92" };

function wrapText(text: string, maxCharsPerLine: number = 20): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let currentLine = "";

  words.forEach((word) => {
    if ((currentLine + " " + word).trim().length <= maxCharsPerLine) {
      currentLine = (currentLine + " " + word).trim();
    } else {
      if (currentLine) lines.push(currentLine);
      currentLine = word;
    }
  });
  if (currentLine) lines.push(currentLine);
  return lines;
}

export default function MemoryGraph({ memories }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 640, height: 520 });
  const [selected, setSelected] = useState<any | null>(memories.find((memory) => memory.memory_type === "correction") || memories.find((memory) => !memory.is_superseded) || null);

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

  const graph = useMemo(() => {
    const nodes = memories.map((memory) => ({ id: memory.id || memory.memory_id, name: text(memory), val: Math.max(3.5, (memory.importance_score ?? confidence(memory)) * 10), color: colors[nodeKind(memory)], confidence: confidence(memory), memory }));
    const links: any[] = [];
    memories.forEach((memory) => {
      const id = memory.id || memory.memory_id;
      if (memory.superseded_by_id) links.push({ source: id, target: memory.superseded_by_id, kind: "correction", color: "rgba(246,185,59,.5)" });
      const supersedes = memory.evidence?.supersedes?.memory_id;
      if (supersedes && !links.some((link) => link.source === supersedes && link.target === id)) links.push({ source: supersedes, target: id, kind: "correction", color: "rgba(246,185,59,.5)" });
    });
    const active = nodes.filter((node) => !node.memory.is_superseded);
    active.slice(1).forEach((node, index) => links.push({ source: active[index].id, target: node.id, kind: "reinforcement", color: "rgba(66,211,232,.16)" }));
    return { nodes, links };
  }, [memories]);

  const supersededBy = selected?.superseded_by_id ? memories.find((memory) => (memory.id || memory.memory_id) === selected.superseded_by_id) : null;
  const sourceQuote = selected?.evidence?.source_quote || selected?.source_quote;

  return <div className="memory-rich-state">
    <div className="graph-layout">
      <section className="panel graph-panel" aria-label="Interactive Volta memory map">
        <header><div><p className="eyebrow">Relationship map</p><h2>Homeowner evidence</h2></div><span className="pill"><MousePointer2 size={13} /> Select a memory</span></header>
        <div ref={ref} className="graph-canvas"><ForceGraph2D width={dimensions.width} height={dimensions.height} graphData={graph} backgroundColor="#0A1728" nodeLabel={(node: any) => `${node.name} · ${Math.round(node.confidence * 100)}% confidence`} nodeColor={(node: any) => node.color} nodeRelSize={6} linkColor={(link: any) => link.color} linkWidth={(link: any) => link.kind === "correction" ? 2.5 : 1} linkDirectionalArrowLength={(link: any) => link.kind === "correction" ? 5 : 0} onNodeClick={(node: any) => setSelected(node.memory)} nodeCanvasObjectMode={() => "after"}         nodeCanvasObject={(node: any, context, scale) => {
          if (scale < 0.9) return;
          const maxLines = 3;
          const rawLines = wrapText(node.name, 18);
          const lines = rawLines.slice(0, maxLines);
          if (rawLines.length > maxLines) {
            lines[maxLines - 1] += "…";
          }
          
          const fontSize = Math.max(9, 11 / scale);
          context.font = `600 ${fontSize}px 'Manrope', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
          context.fillStyle = node.memory.is_superseded ? "#9FB0C3" : "#F4F7FB";
          context.textAlign = "center";
          context.textBaseline = "top";
          
          const lineHeight = fontSize * 1.25;
          const radius = Math.sqrt(node.val || 10) * 1.5;
          const startY = node.y + radius + 4;
          
          lines.forEach((line, i) => {
            context.fillText(line, node.x, startY + i * lineHeight);
          });
        }} /> </div>
        <footer aria-label="Memory map legend"><span><i className="legend-dot gold" /> Active facts</span><span><i className="legend-dot violet" /> Preferences</span><span><i className="legend-dot cyan" /> Evidence</span><span><i className="legend-dot muted-dot" /> Superseded</span><span><Link2 size={12} /> Links show reinforcement or correction</span></footer>
      </section>

      <aside className="panel evidence-panel" aria-live="polite">
        {selected ? <><div className="evidence-title"><div><p className="eyebrow">Selected memory</p><h2>{nodeKind(selected) === "superseded" ? "No longer used" : "Current evidence"}</h2></div><span className={`status-badge ${selected.is_superseded ? "inactive" : "active"}`}>{selected.is_superseded ? "Superseded" : "Current"}</span></div>
          <blockquote><Quote size={15} /> {sourceQuote || text(selected)}</blockquote>
          {!sourceQuote && <p className="source-note">The stored observation is shown because a verbatim source quote is not available in this response.</p>}
          <dl><div><dt>Confidence</dt><dd>{Math.round(confidence(selected) * 100)}%</dd></div><div><dt>Last confirmed</dt><dd>{dateLabel(selected.last_reinforced_at)}</dd></div><div><dt>Type</dt><dd>{selected.memory_type || "Evidence"}</dd></div><div><dt>Importance</dt><dd>{selected.importance_score == null ? "Not scored" : `${Math.round(selected.importance_score * 100)}%`}</dd></div>{supersededBy && <div><dt>Superseded by</dt><dd>{text(supersededBy)}</dd></div>}</dl>
          <p className="privacy-note"><ShieldCheck size={14} /> Memory is on. Current facts may guide advice; superseded facts remain only for accountability.</p>
        </> : <div className="evidence-empty"><span className="icon-box"><Focus size={18} /></span><h2>Select a memory</h2><p>Inspect its status, confidence, and correction relationship.</p></div>}
      </aside>
    </div>

    <section className="panel memory-list-panel"><header><div><p className="eyebrow">Accessible view</p><h2>Memory timeline</h2></div><span className="muted">Select any row to inspect it</span></header><div className="memory-list">{[...memories].sort((a, b) => Number(Boolean(a.is_superseded)) - Number(Boolean(b.is_superseded))).map((memory) => <button key={memory.id || memory.memory_id} className={`memory-list-item ${selected === memory ? "selected" : ""}`} onClick={() => setSelected(memory)}><span className={`memory-type-dot ${nodeKind(memory)}`} /><span className="memory-list-copy"><strong>{text(memory)}</strong><small><Clock3 size={12} /> {dateLabel(memory.last_reinforced_at)} · {Math.round(confidence(memory) * 100)}% confidence</small></span><span className={`status-badge ${memory.is_superseded ? "inactive" : "active"}`}>{memory.is_superseded ? <Eye size={12} /> : <Check size={12} />}{memory.is_superseded ? "Retained" : "Used"}</span></button>)}</div></section>
  </div>;
}
