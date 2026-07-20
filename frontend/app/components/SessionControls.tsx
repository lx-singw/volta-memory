import { ArrowRight, CheckCircle2, LoaderCircle } from "lucide-react";

type Props = {
  sessionActive: boolean;
  loading: boolean;
  onStart: () => void;
  onEnd: () => void;
  endButtonRef?: React.RefObject<HTMLButtonElement>;
};

export default function SessionControls({ sessionActive, loading, onStart, onEnd, endButtonRef }: Props) {
  if (sessionActive) {
    return <button ref={endButtonRef} type="button" onClick={onEnd} disabled={loading} className="button session-end">
      {loading ? <LoaderCircle className="spin-icon" size={16} /> : <CheckCircle2 size={16} />}
      {loading ? "Saving memory…" : "End & remember"}
    </button>;
  }
  return <button type="button" onClick={onStart} disabled={loading} className="button button-primary session-start">
    {loading ? <LoaderCircle className="spin-icon" size={16} /> : null}
    {loading ? "Opening consultation…" : "Start consultation"}
    <ArrowRight size={17} />
  </button>;
}
