import { Bot, ChevronDown, Quote, User } from "lucide-react";

type Props = { role: "user" | "assistant"; content: string; memoryContext?: any[]; explainTrace?: { referenced_memory_ids: string[]; primary_influence_memory_id: string | null; confidence_tier_choice: string | null; counterfactual: string | null } };

const memoryText = (item: any) => item?.content || item?.observation || item?.text || null;

export default function ChatMessage({ role, content, memoryContext, explainTrace }: Props) {
  const evidence = Array.isArray(memoryContext) ? memoryContext.filter(memoryText) : [];
  const hasWhy = !!explainTrace || evidence.length > 0;
  return (
    <article className={`message ${role}`} aria-label={`${role} message`}>
      <div className="message-avatar">{role === "assistant" ? <Bot size={17} /> : <User size={17} />}</div>
      <div className="message-body">
        <div className="message-role">{role === "assistant" ? "Volta" : "You"}</div>
        <div className="message-content">{content}</div>
        {role === "assistant" && hasWhy && (
          <details className="advice-details">
            <summary><span><Quote size={15} /> Why this advice</span><ChevronDown size={15} className="chevron" /></summary>
            <div className="evidence-body">
              {explainTrace?.confidence_tier_choice && <div className="evidence-row"><span>Confidence</span><strong>{explainTrace.confidence_tier_choice}</strong></div>}
              {explainTrace?.primary_influence_memory_id && <div className="evidence-row"><span>Primary memory</span><code>{explainTrace.primary_influence_memory_id}</code></div>}
              {evidence.map((item, index) => <blockquote key={item.memory_id || item.id || index}>{memoryText(item)}{item.is_superseded && <span className="superseded">Superseded</span>}</blockquote>)}
              {explainTrace?.counterfactual && <p className="counterfactual"><strong>If this were different:</strong> {explainTrace.counterfactual}</p>}
              {!evidence.length && explainTrace?.referenced_memory_ids?.length ? <p className="evidence-note">Based on {explainTrace.referenced_memory_ids.length} stored {explainTrace.referenced_memory_ids.length === 1 ? "memory" : "memories"}. Source text is not available in this response.</p> : null}
            </div>
          </details>
        )}
      </div>
    </article>
  );
}
