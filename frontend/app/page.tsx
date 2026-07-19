"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessage from "./components/ChatMessage";
import SessionControls from "./components/SessionControls";
import { Mic, Send, Sun, BatteryCharging } from "lucide-react";

type ChatEntry = {
  role: "user" | "assistant";
  content: string;
  memoryContext?: unknown[];
  explainTrace?: {
    referenced_memory_ids: string[];
    primary_influence_memory_id: string | null;
    confidence_tier_choice: string | null;
    counterfactual: string | null;
  };
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ENTITY_ID = process.env.NEXT_PUBLIC_DEMO_ENTITY_ID || "demo-consumer-1";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Voice State
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = false;
        
        recognitionRef.current.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setInput(transcript);
        };
        
        recognitionRef.current.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          setIsRecording(false);
        };
        
        recognitionRef.current.onend = () => {
          setIsRecording(false);
        };
      }
    }
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition not supported in this browser. Try Chrome.");
      return;
    }
    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  const speak = (text: string) => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      const cleanText = text.replace(/[*#_]/g, ""); 
      const utterance = new SpeechSynthesisUtterance(cleanText);
      const voices = window.speechSynthesis.getVoices();
      const premiumVoice = voices.find(v => v.lang === "en-US" && v.name.includes("Google")) || voices[0];
      if (premiumVoice) utterance.voice = premiumVoice;
      window.speechSynthesis.speak(utterance);
    }
  };

  async function startSession() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/sessions?entity_id=${ENTITY_ID}`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSessionId(data.session_id);
      setMessages([{ role: "assistant", content: "Hello. I am Volta, your Premium Solar Concierge. I remember our past consultations. How can I assist you with your home energy transition today?" }]);
      speak("Hello. I am Volta, your Premium Solar Concierge. I remember our past consultations. How can I assist you with your home energy transition today?");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage() {
    if (!sessionId || !input.trim()) return;
    setLoading(true);
    setError(null);
    const userText = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);

    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { 
          role: "assistant", 
          content: data.reply, 
          memoryContext: data.memory_context_used,
          explainTrace: data.explain_trace 
        },
      ]);
      speak(data.reply);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  }

  async function endSession() {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/end`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      setSessionId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to end session");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#020617", color: "#f8fafc", fontFamily: "sans-serif" }}>
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 0.95; box-shadow: 0 0 15px #facc15; } 50% { opacity: 0.65; box-shadow: 0 0 5px #facc15; } }
        .spinner { border: 3px solid rgba(250, 204, 21, 0.2); width: 36px; height: 36px; border-radius: 50%; border-left-color: #facc15; animation: spin 1s linear infinite; }
        .pulse-btn { animation: pulse 1.5s infinite; }
      ` }} />

      <div style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "1rem" }}>
          <Sun size={36} color="#facc15" />
          <h1 style={{ margin: 0, fontSize: "2.2rem", fontWeight: 600, letterSpacing: "-0.02em" }}>Volta Concierge</h1>
        </div>
        <p style={{ color: "#94a3b8", fontSize: "1.1rem", marginBottom: "2rem", display: "flex", alignItems: "center", gap: "8px" }}>
          <BatteryCharging size={20} color="#38bdf8" /> Premium Home Energy Profile: {ENTITY_ID}
        </p>
        
        <SessionControls sessionActive={!!sessionId} loading={loading} onStart={startSession} onEnd={endSession} />
        {error && <div style={{ marginTop: "1rem", color: "#f87171", background: "rgba(248,113,113,0.1)", padding: "1rem", borderRadius: "8px" }}>{error}</div>}

        {loading && !sessionId && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "3rem", margin: "2rem 0", borderRadius: 16, background: "rgba(30, 41, 59, 0.6)", border: "1px solid rgba(250, 204, 21, 0.2)", backdropFilter: "blur(8px)" }}>
            <div className="spinner"></div>
            <p style={{ marginTop: "1.25rem", color: "#facc15", fontWeight: 600 }}>Initializing Neural Memory Core...</p>
          </div>
        )}

        <div style={{ marginTop: "2rem", minHeight: 400, paddingBottom: "100px" }}>
          {messages.map((msg, idx) => (
            <ChatMessage key={idx} role={msg.role} content={msg.content} memoryContext={msg.memoryContext} explainTrace={msg.explainTrace} />
          ))}
        </div>

        {/* Input Dock */}
        <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, background: "linear-gradient(to top, #020617 80%, transparent)", padding: "2rem" }}>
          <div style={{ maxWidth: 800, margin: "0 auto", display: "flex", gap: "12px", alignItems: "center", background: "#0f172a", padding: "0.5rem", borderRadius: "100px", border: "1px solid #1e293b", boxShadow: "0 10px 25px rgba(0,0,0,0.5)" }}>
            <button 
              onClick={toggleRecording} 
              disabled={!sessionId || loading} 
              className={isRecording ? "pulse-btn" : ""}
              style={{ width: "50px", height: "50px", borderRadius: "50%", border: "none", background: isRecording ? "#ef4444" : "#1e293b", color: isRecording ? "white" : "#94a3b8", cursor: (!sessionId || loading) ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.2s" }}
            >
              <Mic size={24} />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Speak or type your energy query..."
              disabled={!sessionId || loading}
              style={{ flex: 1, padding: "1rem", borderRadius: "100px", border: "none", background: "transparent", color: "#f8fafc", fontSize: "1.05rem", outline: "none" }}
            />
            <button 
              onClick={sendMessage} 
              disabled={!sessionId || loading || !input.trim()} 
              style={{ width: "50px", height: "50px", borderRadius: "50%", border: "none", background: (!sessionId || loading || !input.trim()) ? "#1e293b" : "#facc15", color: (!sessionId || loading || !input.trim()) ? "#475569" : "#020617", cursor: (!sessionId || loading || !input.trim()) ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.2s" }}
            >
              <Send size={24} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
