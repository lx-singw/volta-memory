type MemoryRow = {
  id?: string;
  memory_type?: string;
  observation?: string;
  base_confidence?: number;
  effective_confidence?: number;
  reinforcement_count?: number;
  is_superseded?: boolean;
  last_reinforced_at?: string | null;
};

type Props = {
  memories: MemoryRow[];
};

export default function MemoryTable({ memories }: Props) {
  if (!memories.length) {
    return <p style={{ color: "#94a3b8" }}>No memories yet — complete a session to extract observations.</p>;
  }

  return (
    <div style={{ overflowX: "auto", marginTop: "1rem" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #334155" }}>
            <th style={th}>Type</th>
            <th style={th}>Observation</th>
            <th style={th}>Base</th>
            <th style={th}>Effective</th>
            <th style={th}>Reinforcements</th>
            <th style={th}>Superseded</th>
          </tr>
        </thead>
        <tbody>
          {memories.map((row) => (
            <tr key={row.id} style={{ borderBottom: "1px solid #1e293b" }}>
              <td style={td}>{row.memory_type}</td>
              <td style={td}>{row.observation}</td>
              <td style={td}>{row.base_confidence?.toFixed?.(2)}</td>
              <td style={td}>{row.effective_confidence?.toFixed?.(2)}</td>
              <td style={td}>{row.reinforcement_count}</td>
              <td style={td}>{row.is_superseded ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const th: React.CSSProperties = { padding: "0.5rem", color: "#94a3b8" };
const td: React.CSSProperties = { padding: "0.5rem", verticalAlign: "top" };
