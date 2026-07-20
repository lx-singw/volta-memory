import { ArrowRight, CheckCircle2 } from "lucide-react";

type Props = { sessionActive: boolean; loading: boolean; onStart: () => void; onEnd: () => void };

export default function SessionControls({ sessionActive, loading, onStart, onEnd }: Props) {
  if (sessionActive) return <button onClick={onEnd} disabled={loading} className="button"><CheckCircle2 size={16} /> End & remember</button>;
  return <button onClick={onStart} disabled={loading} className="button button-primary session-start">{loading ? "Opening consultation…" : "Start consultation"}<ArrowRight size={17} /></button>;
}
