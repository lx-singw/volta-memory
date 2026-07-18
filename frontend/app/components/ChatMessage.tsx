type Props = {
  role: "user" | "assistant";
  content: string;
  memoryContext?: any[];
  explainTrace?: {
    referenced_memory_ids: string[];
    primary_influence_memory_id: string | null;
    confidence_tier_choice: string | null;
    counterfactual: string | null;
  };
};

export default function ChatMessage({ role, content, memoryContext, explainTrace }: Props) {
  return (
    <div
      style={{
        marginBottom: "0.75rem",
        padding: "0.75rem 1rem",
        borderRadius: 8,
        background: role === "user" ? "#1e293b" : "#172554",
        border: "1px solid #334155",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 4 }}>{role}</div>
      <div>{content}</div>
      {role === "assistant" && explainTrace && (
        <details style={{ marginTop: 8, fontSize: 12, color: "#cbd5e1", background: "rgba(15, 23, 42, 0.6)", padding: "0.5rem", borderRadius: "4px", border: "1px solid #1e3a8a" }}>
          <summary style={{ cursor: "pointer", fontWeight: 600, color: "#facc15" }}>Explainability Trace (Cognitive Logic)</summary>
          <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
            <div><strong>Primary Influence Memory ID:</strong> {explainTrace.primary_influence_memory_id || "None"}</div>
            <div><strong>Selected Confidence Tier:</strong> <span style={{ color: "#38bdf8" }}>{explainTrace.confidence_tier_choice || "Default"}</span></div>
            {explainTrace.counterfactual && (
              <div><strong>Counterfactual Logic:</strong> <span style={{ fontStyle: "italic", color: "#94a3b8" }}>"{explainTrace.counterfactual}"</span></div>
            )}
          </div>
        </details>
      )}
      {role === "assistant" && memoryContext && Array.isArray(memoryContext) && memoryContext.length > 0 && (
        <details style={{ marginTop: 8, fontSize: 12, color: "#cbd5e1" }}>
          <summary style={{ cursor: "pointer" }}>Memory context used ({memoryContext.length})</summary>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(memoryContext, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
