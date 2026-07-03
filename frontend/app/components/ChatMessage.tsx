type Props = {
  role: "user" | "assistant";
  content: string;
  memoryContext?: unknown[];
};

export default function ChatMessage({ role, content, memoryContext }: Props) {
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
      {role === "assistant" && memoryContext && Array.isArray(memoryContext) && memoryContext.length > 0 && (
        <details style={{ marginTop: 8, fontSize: 12, color: "#cbd5e1" }}>
          <summary>Memory context used ({memoryContext.length})</summary>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(memoryContext, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
