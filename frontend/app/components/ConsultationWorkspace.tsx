"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { BatteryCharging, CheckCircle2, CircleAlert, Download, KeyRound, Mic, RefreshCcw, Send, ShieldCheck, Sparkles, SunMedium, Trash2 } from "lucide-react";
import ChatMessage from "./ChatMessage";
import MemoryReceipt from "./MemoryReceipt";
import SessionControls from "./SessionControls";
import { ApiError, getRuntimeConfig, type EndSessionResult, type MemoryDTO, type ProfileDTO, type ProfileFact, type RuntimeConfig, VoltaApi } from "../lib/api";

type WorkspaceMode = "personal" | "try";
type ConsultationState = "idle" | "active" | "ending" | "complete" | "error";
type Action = "starting" | "sending" | "ending" | null;
type Entry = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: string | null;
  failed?: boolean;
  memoryContext?: MemoryDTO[];
  explainTrace?: import("../lib/api").ExplainTrace | null;
};

const SLOT_LABELS: Array<[string, string]> = [
  ["monthly_bill", "Electricity bill"],
  ["backup_priority", "Backup priority"],
  ["roof_home", "Roof & home"],
  ["budget", "Budget"],
];

function stateKey(mode: WorkspaceMode, suffix: string) {
  return `volta:${mode}:${suffix}`;
}

function newId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "Not yet confirmed";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Not yet confirmed" : new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(date);
}

function statusLabel(status: ProfileFact["status"] | MemoryDTO["status"]) {
  if (status === "eligible") return "Current";
  if (status === "needs_reconfirmation") return "Needs reconfirmation";
  if (status === "retained") return "Retained for audit";
  return "Excluded from advice";
}

function statusClass(status: ProfileFact["status"] | MemoryDTO["status"]) {
  return status === "eligible" ? "active" : status === "needs_reconfirmation" ? "warning" : "inactive";
}

function ProfileRail({ profile, memories, loading, api, onWorkspaceDeleted }: { profile: ProfileDTO | null; memories: MemoryDTO[]; loading: boolean; api: VoltaApi | null; onWorkspaceDeleted: () => Promise<void> }) {
  const slotFacts = new Map((profile?.facts || []).map((fact) => [fact.profileSlot, fact]));
  const remembered = memories.slice(0, 4);
  return <aside className="context-rail" aria-label="Current confirmed energy profile">
    <section className="panel profile-panel">
      <div className="section-head"><span className="icon-box"><BatteryCharging size={18} /></span><div><p className="eyebrow">Energy profile</p><h2>Current confirmed facts</h2></div></div>
      <dl className="profile-list">
        {SLOT_LABELS.slice(0, 3).map(([slot, label]) => {
          const fact = slotFacts.get(slot);
          return <div key={slot}><dt>{label}</dt><dd>{loading ? "Loading…" : fact ? <>
            <span>{fact.displayValue}</span>
            <small className={`status-badge ${statusClass(fact.status)}`}>{statusLabel(fact.status)}</small>
            <small className="profile-fact-meta">Confirmed {formatDate(fact.lastConfirmedAt)} · {fact.confidence === null ? "Confidence not scored" : `${Math.round(fact.confidence * 100)}% confidence`}</small>
            {fact.sourceMemoryId ? <Link className="profile-source-link" href={`/memory?focus=${encodeURIComponent(fact.sourceMemoryId)}`} aria-label={`Inspect the source record for ${label}`}>
              {fact.sourceVerified ? `Inspect verified source${fact.sourceTurnIndex === null || fact.sourceTurnIndex === undefined ? "" : ` · turn ${fact.sourceTurnIndex}`}` : "Inspect stored record"}
            </Link> : null}
          </> : "Unknown"}</dd></div>;
        })}
        <div><dt>Last confirmed</dt><dd>{formatDate(profile?.lastConfirmedAt)}</dd></div>
      </dl>
      <p className="honesty-note"><ShieldCheck size={15} /> Unknown facts stay unknown until you confirm them.</p>
    </section>

    <section className="card remembered" aria-live="polite">
      <div className="section-head compact"><SunMedium size={17} /><h2>What Volta remembers</h2></div>
      {loading ? <p>Loading verified context…</p> : remembered.length ? <ul>{remembered.map((memory) => <li key={memory.id}>{memory.observation}<span className={`status-badge ${statusClass(memory.status)}`}>{statusLabel(memory.status)}</span></li>)}</ul> : <p>No confirmed context is loaded yet.</p>}
    </section>
    <AccountPrivacyControls api={api} onWorkspaceDeleted={onWorkspaceDeleted} />
  </aside>;
}

function AccountPrivacyControls({ api, onWorkspaceDeleted }: { api: VoltaApi | null; onWorkspaceDeleted: () => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [working, setWorking] = useState<"link" | "export" | "delete" | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const requestLink = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!api || !email.trim()) return;
    setWorking("link");
    setStatus(null);
    try {
      await api.getWorkspace();
      await api.requestMagicLink(email.trim());
      setStatus("If this address can receive mail, a secure sign-in link is on its way.");
      setEmail("");
    } catch (cause) {
      setStatus(cause instanceof Error ? cause.message : "Volta could not send a sign-in link.");
    } finally {
      setWorking(null);
    }
  };

  const exportWorkspace = async () => {
    if (!api) return;
    setWorking("export");
    setStatus(null);
    try {
      const data = await api.exportWorkspace();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const download = document.createElement("a");
      download.href = url;
      download.download = `volta-memory-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(download);
      download.click();
      download.remove();
      URL.revokeObjectURL(url);
      setStatus("Your memory export was downloaded.");
    } catch (cause) {
      setStatus(cause instanceof Error ? cause.message : "Volta could not export this workspace.");
    } finally {
      setWorking(null);
    }
  };

  const deleteWorkspace = async () => {
    if (!api || !confirmDelete) return;
    setWorking("delete");
    setStatus(null);
    try {
      await api.getWorkspace();
      await api.deleteWorkspace();
      await onWorkspaceDeleted();
      setConfirmDelete(false);
      setStatus("This workspace was permanently deleted. You now have a fresh private workspace.");
    } catch (cause) {
      setStatus(cause instanceof Error ? cause.message : "Volta could not delete this workspace.");
    } finally {
      setWorking(null);
    }
  };

  return <section className="card account-privacy" aria-label="Account and privacy controls">
    <details>
      <summary><ShieldCheck size={16} /> Account &amp; privacy</summary>
      <div className="account-privacy-body">
        <p>Keep this private workspace across devices with a passwordless sign-in, or take a portable copy of your stored evidence.</p>
        <form className="magic-link-form" onSubmit={(event) => void requestLink(event)}>
          <label htmlFor="account-email">Email for secure sign-in</label>
          <div><input id="account-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" disabled={!api || working !== null} required /><button type="submit" className="button" disabled={!api || working !== null || !email.trim()}><KeyRound size={14} /> {working === "link" ? "Sending…" : "Send link"}</button></div>
        </form>
        <div className="privacy-actions"><button type="button" className="button" onClick={() => void exportWorkspace()} disabled={!api || working !== null}><Download size={14} /> {working === "export" ? "Preparing…" : "Export memory"}</button><button type="button" className="button button-danger" onClick={() => setConfirmDelete((value) => !value)} disabled={!api || working !== null}><Trash2 size={14} /> Delete workspace</button></div>
        {confirmDelete ? <div className="delete-confirmation"><p>Deletion permanently removes this workspace’s conversations and memory records. This cannot be undone.</p><button type="button" className="button button-danger" onClick={() => void deleteWorkspace()} disabled={!api || working !== null}>{working === "delete" ? "Deleting…" : "Permanently delete"}</button></div> : null}
        {status ? <p className="account-status" aria-live="polite">{status}</p> : null}
      </div>
    </details>
  </section>;
}

export default function ConsultationWorkspace({ mode = "personal" }: { mode?: WorkspaceMode }) {
  const [api, setApi] = useState<VoltaApi | null>(null);
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  const [state, setState] = useState<ConsultationState>("idle");
  const [action, setAction] = useState<Action>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Entry[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [retryMessage, setRetryMessage] = useState<{ id: string; content: string } | null>(null);
  const [profile, setProfile] = useState<ProfileDTO | null>(null);
  const [memories, setMemories] = useState<MemoryDTO[]>([]);
  const [contextLoading, setContextLoading] = useState(true);
  const [receipt, setReceipt] = useState<EndSessionResult | null>(null);
  const [recording, setRecording] = useState(false);
  const recognition = useRef<any>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const endButtonRef = useRef<HTMLButtonElement>(null);
  const tryWorkspaceSetup = useRef<{ api: VoltaApi; promise: Promise<void> } | null>(null);

  useEffect(() => {
    let alive = true;
    void getRuntimeConfig().then((loaded) => {
      if (!alive) return;
      setConfig(loaded);
      setApi(new VoltaApi(loaded));
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    try {
      const storedSession = sessionStorage.getItem(stateKey(mode, "session"));
      const storedMessages = sessionStorage.getItem(stateKey(mode, "messages"));
      if (storedSession) {
        setSessionId(storedSession);
        setState("active");
      }
      if (storedMessages) setMessages(JSON.parse(storedMessages) as Entry[]);
    } catch {
      sessionStorage.removeItem(stateKey(mode, "session"));
      sessionStorage.removeItem(stateKey(mode, "messages"));
    }
  }, [mode]);

  useEffect(() => {
    if (!sessionId) sessionStorage.removeItem(stateKey(mode, "session"));
    else sessionStorage.setItem(stateKey(mode, "session"), sessionId);
  }, [mode, sessionId]);

  useEffect(() => {
    if (!messages.length) sessionStorage.removeItem(stateKey(mode, "messages"));
    else sessionStorage.setItem(stateKey(mode, "messages"), JSON.stringify(messages));
  }, [messages, mode]);

  const refreshContext = useCallback(async () => {
    if (!api) return;
    setContextLoading(true);
    const [profileResult, memoriesResult] = await Promise.allSettled([api.getProfile(), api.getMemories()]);
    if (profileResult.status === "fulfilled") setProfile(profileResult.value);
    if (memoriesResult.status === "fulfilled") setMemories(memoriesResult.value.memories);
    setContextLoading(false);
  }, [api]);

  const resetDeletedWorkspace = useCallback(async () => {
    if (!api) return;
    sessionStorage.removeItem(stateKey(mode, "session"));
    sessionStorage.removeItem(stateKey(mode, "messages"));
    setSessionId(null);
    setMessages([]);
    setReceipt(null);
    setError(null);
    setState("idle");
    setProfile(null);
    setMemories([]);
    if (mode === "try") {
      sessionStorage.removeItem(stateKey("try", "workspace"));
      tryWorkspaceSetup.current = null;
      await api.getWorkspace();
      const replacement = await api.createTryWorkspace();
      sessionStorage.setItem(stateKey("try", "workspace"), replacement.entityId);
    } else {
      await api.getWorkspace();
    }
    await refreshContext();
  }, [api, mode, refreshContext]);

  useEffect(() => {
    if (!api) return;
    if (mode === "try") {
      // Bootstrap through /v1/me first. That gives a same-origin browser a
      // real CSRF token before it can ask the server to replace its workspace.
      // The stored id lets a reload preserve this private sandbox instead of
      // silently creating a new tenant or reusing the personal workspace.
      let alive = true;
      const existing = tryWorkspaceSetup.current?.api === api ? tryWorkspaceSetup.current : null;
      const setup = existing?.promise || (async () => {
        const current = await api.getWorkspace();
        const workspaceKey = stateKey("try", "workspace");
        const storedWorkspaceId = sessionStorage.getItem(workspaceKey);
        if (storedWorkspaceId === current.entityId) return;

        const workspace = await api.createTryWorkspace();
        sessionStorage.setItem(workspaceKey, workspace.entityId);
        // A persisted transcript/session belongs to the old entity. Clear it
        // before any request can be made through the replacement cookie.
        sessionStorage.removeItem(stateKey("try", "session"));
        sessionStorage.removeItem(stateKey("try", "messages"));
        setSessionId(null);
        setMessages([]);
        setReceipt(null);
        setState("idle");
      })();
      if (!existing) tryWorkspaceSetup.current = { api, promise: setup };
      void setup.then(async () => {
        if (!alive) return;
        await refreshContext();
      }).catch((cause) => {
        if (!alive) return;
        const message = cause instanceof ApiError && cause.status === 403
          ? "Volta could not securely start a private workspace. Refresh and try again."
          : "Volta could not create a private workspace.";
        setError(message);
        setState("error");
      });
      return () => { alive = false; };
    } else {
      void refreshContext();
    }
  }, [api, mode, refreshContext]);

  useEffect(() => {
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition) return;
    const instance = new Recognition();
    instance.continuous = false;
    instance.interimResults = false;
    instance.onresult = (event: any) => setInput(event.results[0][0].transcript);
    instance.onerror = () => setRecording(false);
    instance.onend = () => setRecording(false);
    recognition.current = instance;
    return () => instance.abort?.();
  }, []);

  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, action]);

  const listen = useCallback((text: string) => {
    if (!window.speechSynthesis) {
      setError("Listen is not supported in this browser.");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/[*#_]/g, ""));
    const voice = window.speechSynthesis.getVoices().find((candidate) => candidate.lang === "en-ZA") || window.speechSynthesis.getVoices().find((candidate) => candidate.lang.startsWith("en"));
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
  }, []);

  const toggleRecording = () => {
    if (!recognition.current) {
      setError("Voice input is not supported in this browser. You can still type your answer.");
      return;
    }
    if (recording) recognition.current.stop();
    else {
      setError(null);
      recognition.current.start();
      setRecording(true);
    }
  };

  const startSession = async () => {
    if (!api || action) return;
    setAction("starting");
    setError(null);
    try {
      const created = await api.startSession();
      const opening = created.openingMessage || "Welcome. Tell me what you want to solve for your home energy setup.";
      setSessionId(created.sessionId);
      setMessages([{ id: newId(), role: "assistant", content: opening, createdAt: new Date().toISOString() }]);
      setState("active");
      await refreshContext();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Volta could not start this consultation.");
      setState("error");
    } finally {
      setAction(null);
    }
  };

  const sendMessage = async (retry?: { id: string; content: string }) => {
    if (!api || !sessionId || action) return;
    const content = retry?.content || input.trim();
    if (!content) return;
    const entryId = retry?.id || newId();
    setAction("sending");
    setError(null);
    setInput("");
    setRetryMessage(null);
    if (retry) setMessages((current) => current.map((entry) => entry.id === entryId ? { ...entry, failed: false } : entry));
    else setMessages((current) => [...current, { id: entryId, role: "user", content, createdAt: new Date().toISOString() }]);
    try {
      const response = await api.sendMessage(sessionId, content);
      setMessages((current) => [...current, { id: newId(), role: "assistant", content: response.reply, createdAt: new Date().toISOString(), memoryContext: response.memoryContext, explainTrace: response.explainTrace }]);
      await refreshContext();
    } catch (cause) {
      setMessages((current) => current.map((entry) => entry.id === entryId ? { ...entry, failed: true } : entry));
      setInput(content);
      setRetryMessage({ id: entryId, content });
      setError(cause instanceof Error ? cause.message : "Volta could not send that message.");
      setState("error");
    } finally {
      setAction(null);
    }
  };

  const endSession = async () => {
    if (!api || !sessionId || action) return;
    setAction("ending");
    setState("ending");
    setError(null);
    const storageKey = stateKey(mode, `end:${sessionId}`);
    const idempotencyKey = sessionStorage.getItem(storageKey) || newId();
    sessionStorage.setItem(storageKey, idempotencyKey);
    try {
      const result = await api.endSession(sessionId, idempotencyKey);
      setReceipt(result);
      setSessionId(null);
      setState("complete");
      await refreshContext();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Volta could not save this consultation.");
      setState("active");
    } finally {
      setAction(null);
    }
  };

  const activeFacts = profile?.currentFactCount || 0;
  const retainedFacts = profile?.retainedFactCount || 0;
  // A transient send error must not hide an otherwise live session or strand
  // the user's draft. `state` records the error while the server-issued id is
  // still the source of truth for whether the consultation remains active.
  const active = Boolean(sessionId) && state !== "complete";
  const loading = action !== null;
  const phaseCopy = useMemo(() => {
    if (state === "ending") return { label: "Saving confirmed memory", title: "Recording this consultation", detail: "Volta is extracting only confirmed facts and preserving any correction history." };
    if (state === "complete") return { label: "Consultation complete", title: "Your conversation is still here", detail: "Review the memory receipt, then start a new consultation when something changes." };
    if (active) return { label: "Consultation active", title: "Continue your consultation", detail: "Tell Volta what changed. Advice will include its supporting memory." };
    return { label: mode === "try" ? "Private trial workspace" : "Ready when you are", title: "One clear place to begin", detail: "Start a consultation to save only the facts you confirm." };
  }, [active, mode, state]);

  return <div className="page-wrap consultation-page">
    {!active ? <section className="consult-hero">
      <div><p className="eyebrow">{mode === "try" ? "Private trial workspace" : "Persistent solar guidance"}</p><h1 className="display">Your home energy decision,<br />with context intact.</h1><p>Volta remembers the facts you confirm, notices when they change, and shows the evidence behind every recommendation.</p></div>
      <SessionControls sessionActive={false} loading={loading} onStart={startSession} onEnd={endSession} />
    </section> : <section className="session-strip" aria-label="Active consultation status"><span className="pill"><span className="dot" /> Consultation active</span><strong>{activeFacts} {activeFacts === 1 ? "fact" : "facts"} eligible · {retainedFacts} {retainedFacts === 1 ? "prior fact" : "prior facts"} retained for audit</strong><SessionControls sessionActive loading={loading} onStart={startSession} onEnd={endSession} endButtonRef={endButtonRef} /></section>}

    {error ? <div className="error consultation-error" role="alert"><CircleAlert size={17} /><span>{error}</span>{retryMessage ? <button type="button" className="button retry-button" onClick={() => void sendMessage(retryMessage)} disabled={loading}><RefreshCcw size={15} /> Retry message</button> : state === "error" && !active ? <button type="button" className="button retry-button" onClick={startSession} disabled={loading}><RefreshCcw size={15} /> Try again</button> : null}</div> : null}

    <div className="workspace">
      <ProfileRail profile={profile} memories={memories} loading={contextLoading || !config} api={api} onWorkspaceDeleted={resetDeletedWorkspace} />
      <section className={`panel chat-panel ${!active ? "chat-panel-ready" : ""}`} aria-label="Volta consultation">
        <header className="chat-head"><div><span className="pill"><span className="dot" /> {phaseCopy.label}</span><h2>{phaseCopy.title}</h2><p>{phaseCopy.detail}</p></div></header>
        {active || messages.length ? <>
          <div ref={messagesRef} className="message-list" aria-live="polite" aria-busy={loading}>
            {messages.map((message) => <div key={message.id} className={message.failed ? "message-failed" : undefined}><ChatMessage {...message} onListen={message.role === "assistant" ? listen : undefined} />{message.failed ? <p className="delivery-error">Message was not delivered. Your draft is preserved below.</p> : null}</div>)}
            {loading && action === "sending" ? <div className="thinking"><span className="spinner" /> Volta is checking your confirmed context…</div> : null}
          </div>
          {active ? <div className="composer">
            <button type="button" className={`voice-button ${recording ? "recording" : ""}`} onClick={toggleRecording} disabled={loading} aria-label={recording ? "Stop recording" : "Start voice input"}><Mic size={19} /></button>
            <label className="sr-only" htmlFor="message">Message Volta</label>
            <input id="message" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.nativeEvent.isComposing) void sendMessage(); }} placeholder="Something changed? Tell Volta." disabled={loading} />
            <button type="button" className="send-button" onClick={() => void sendMessage()} disabled={loading || !input.trim()} aria-label="Send message"><Send size={19} /></button>
          </div> : null}
        </> : <div className="empty-chat"><span className="icon-box large"><Sparkles size={24} /></span><h3>Start with what matters now</h3><p>Volta will ask only for relevant context, keep a source-linked record, and surface exactly what changes.</p></div>}
      </section>
    </div>
    <MemoryReceipt result={receipt} onClose={() => setReceipt(null)} returnFocusTo={endButtonRef} />
  </div>;
}
