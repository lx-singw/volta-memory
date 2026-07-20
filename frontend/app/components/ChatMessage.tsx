import Link from "next/link";
import { Bot, ChevronDown, ExternalLink, Quote, User, Volume2 } from "lucide-react";
import type { ExcludedMemoryTrace, ExplainTrace, MemoryDTO } from "../lib/api";

type Props = {
  role: "user" | "assistant";
  content: string;
  memoryContext?: MemoryDTO[];
  explainTrace?: ExplainTrace | null;
  onListen?: (text: string) => void;
};

function sourceLabel(memory: MemoryDTO): string | null {
  if (!memory.provenance.sourceVerified || !memory.provenance.sourceQuote) return null;
  const turn = memory.provenance.sourceTurnIndex;
  return turn === null || turn === undefined ? "Verified user source" : `Your turn ${turn}`;
}

function EvidenceItem({ memory, label }: { memory: MemoryDTO; label?: string }) {
  const source = sourceLabel(memory);
  return <article className="advice-memory-item">
    <div className="advice-memory-copy">
      {label ? <small className="memory-context-label">{label}</small> : null}
      <strong>{memory.observation}</strong>
      {source ? <span><Quote size={12} /> {source}: “{memory.provenance.sourceQuote}”</span> : <span>Stored observation · source quote unavailable</span>}
    </div>
    <Link href={`/memory?focus=${encodeURIComponent(memory.id)}`} aria-label={`Inspect ${memory.observation} in the memory map`}><ExternalLink size={15} /></Link>
  </article>;
}

function TraceExclusionItem({ item }: { item: ExcludedMemoryTrace }) {
  const source = item.sourceVerified && item.sourceQuote
    ? item.sourceTurnIndex === null || item.sourceTurnIndex === undefined ? "Verified user source" : `Your turn ${item.sourceTurnIndex}`
    : null;
  return <article className="advice-memory-item">
    <div className="advice-memory-copy">
      <small className="memory-context-label">{item.reason || "No exclusion reason was recorded."}</small>
      {item.observation ? <strong>{item.observation}</strong> : <strong>Recorded memory was not used in this answer</strong>}
      {source ? <span><Quote size={12} /> {source}: “{item.sourceQuote}”</span> : null}
    </div>
    <Link href={`/memory?focus=${encodeURIComponent(item.memoryId)}`} aria-label={item.observation ? `Inspect ${item.observation} in the memory map` : "Inspect this memory in the memory map"}><ExternalLink size={15} /></Link>
  </article>;
}

export default function ChatMessage({ role, content, memoryContext = [], explainTrace, onListen }: Props) {
  const usedIds = new Set(explainTrace?.usedMemoryIds?.length ? explainTrace.usedMemoryIds : explainTrace?.referencedMemoryIds || []);
  const excludedTrace = explainTrace?.excludedMemories || [];
  const excludedIds = new Map(excludedTrace.map((item) => [item.memoryId, item.reason]));
  const used = memoryContext.filter((memory) => usedIds.has(memory.id));
  const available = memoryContext.filter((memory) => !usedIds.has(memory.id) && !excludedIds.has(memory.id));
  const excluded = memoryContext.filter((memory) => excludedIds.has(memory.id));
  const traceOnlyExcluded = excludedTrace.filter((item) => !memoryContext.some((memory) => memory.id === item.memoryId));
  const hasWhy = role === "assistant" && (
    used.length > 0 || available.length > 0 || excluded.length > 0 || traceOnlyExcluded.length > 0 ||
    !!explainTrace?.confidenceTierChoice || !!explainTrace?.counterfactual
  );

  return <article className={`message ${role}`} aria-label={`${role} message`}>
    <div className="message-avatar">{role === "assistant" ? <Bot size={17} /> : <User size={17} />}</div>
    <div className="message-body">
      <div className="message-role">
        <span>{role === "assistant" ? "Volta" : "You"}</span>
        {role === "assistant" && onListen ? <button type="button" className="listen-button" onClick={() => onListen(content)} aria-label="Listen to this Volta response"><Volume2 size={14} /> Listen</button> : null}
      </div>
      <div className="message-content">{content}</div>
      {hasWhy ? <details className="advice-details">
        <summary><span><Quote size={15} /> Why this advice</span><ChevronDown size={15} className="chevron" /></summary>
        <div className="evidence-body">
          {used.length ? <section className="advice-group"><h4>Used in this answer</h4>{used.map((memory) => <EvidenceItem key={memory.id} memory={memory} />)}</section> : null}
          {available.length ? <section className="advice-group"><h4>Available context</h4>{available.map((memory) => <EvidenceItem key={memory.id} memory={memory} />)}</section> : null}
          {excluded.length || traceOnlyExcluded.length ? <section className="advice-group"><h4>Not used in this answer</h4>
            {excluded.map((memory) => <EvidenceItem key={memory.id} memory={memory} label={excludedIds.get(memory.id) || memory.exclusionReason || "No exclusion reason was recorded."} />)}
            {traceOnlyExcluded.map((item) => <TraceExclusionItem key={item.memoryId} item={item} />)}
          </section> : null}
          {explainTrace?.confidenceTierChoice ? <div className="evidence-row"><span>Confidence</span><strong>{explainTrace.confidenceTierChoice}</strong></div> : null}
          {explainTrace?.counterfactual ? <p className="counterfactual"><strong>If this changed:</strong> {explainTrace.counterfactual}</p> : null}
        </div>
      </details> : null}
    </div>
  </article>;
}
