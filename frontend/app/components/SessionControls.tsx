type Props = {
  sessionActive: boolean;
  loading: boolean;
  onStart: () => void;
  onEnd: () => void;
};

export default function SessionControls({ sessionActive, loading, onStart, onEnd }: Props) {
  return (
    <div style={{ display: "flex", gap: "0.5rem" }}>
      <button onClick={onStart} disabled={sessionActive || loading} style={btn}>
        Start session
      </button>
      <button onClick={onEnd} disabled={!sessionActive || loading} style={{ ...btn, background: "#b45309" }}>
        End session (extract memories)
      </button>
    </div>
  );
}

const btn: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  borderRadius: 8,
  border: "none",
  background: "#059669",
  color: "white",
  cursor: "pointer",
};
