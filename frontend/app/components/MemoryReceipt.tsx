"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { ArrowRight, CheckCircle2, Quote, X } from "lucide-react";
import type { EndSessionResult, LifecycleChange } from "../lib/api";

type Props = {
  result: EndSessionResult | null;
  onClose: () => void;
  returnFocusTo?: React.RefObject<HTMLButtonElement>;
};

const actionCopy: Record<LifecycleChange["action"], string> = {
  created: "Saved new memory",
  reinforced: "Reinforced memory",
  corrected: "Memory updated",
  excluded: "Excluded from advice",
  reconfirmed: "Reconfirmed memory",
  none: "No durable memory added",
};

function changeTarget(change: LifecycleChange): string | null {
  return change.after?.id || change.before?.id || null;
}

export default function MemoryReceipt({ result, onClose, returnFocusTo }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (result && !dialog.open) dialog.showModal();
    if (!result && dialog.open) dialog.close();
  }, [result]);

  const finishClose = () => {
    onClose();
    window.setTimeout(() => returnFocusTo?.current?.focus(), 0);
  };

  const close = () => {
    const dialog = dialogRef.current;
    if (dialog?.open) dialog.close();
    else finishClose();
  };

  const changes = result?.memoryChanges || [];
  const focusId = changes.map(changeTarget).find(Boolean);

  return (
    <dialog
      ref={dialogRef}
      className="memory-receipt"
      aria-labelledby="memory-receipt-title"
      onCancel={(event) => { event.preventDefault(); close(); }}
      onClose={finishClose}
    >
      <div className="receipt-topline">
        <span className="receipt-icon"><CheckCircle2 size={22} /></span>
        <button className="icon-only" type="button" onClick={close} aria-label="Close memory update receipt"><X size={18} /></button>
      </div>
      <p className="eyebrow">Memory audit receipt</p>
      <h2 id="memory-receipt-title">{changes.some((change) => change.action === "corrected") ? "Memory updated" : "Session remembered"}</h2>
      <p className="receipt-intro">Volta saved only confirmed context and keeps earlier facts visible when they change.</p>

      <div className="receipt-changes" aria-live="polite">
        {changes.length ? changes.map((change, index) => (
          <article className={`receipt-change receipt-${change.action}`} key={`${change.action}-${change.after?.id || change.before?.id || index}`}>
            <strong>{actionCopy[change.action]}</strong>
            {change.action === "corrected" && change.before && change.after ? (
              <>
                <p><span className="receipt-before">{change.before.observation}</span><ArrowRight size={15} /><span>{change.after.observation}</span></p>
                <small>Earlier value retained for accountability and no longer eligible for advice.</small>
              </>
            ) : change.after ? <p>{change.after.observation}</p> : change.before ? <p>{change.before.observation}</p> : <p>No durable memory was added because nothing was confidently confirmed.</p>}
            {change.sourceVerified && change.sourceQuote && <blockquote><Quote size={13} /> “{change.sourceQuote}”{change.sourceTurnIndex !== null && change.sourceTurnIndex !== undefined ? <small> · Your turn {change.sourceTurnIndex}</small> : null}</blockquote>}
          </article>
        )) : <article className="receipt-change receipt-none"><strong>No durable memory added</strong><p>Nothing was confidently confirmed in this consultation.</p></article>}
      </div>

      <div className="receipt-actions">
        {focusId ? <Link className="button button-primary" href={`/memory?focus=${encodeURIComponent(focusId)}`} onClick={close}>Inspect memory map <ArrowRight size={16} /></Link> : null}
        <button className="button" type="button" onClick={close}>Return to consultation</button>
      </div>
    </dialog>
  );
}
