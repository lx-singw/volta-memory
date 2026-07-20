"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, KeyRound } from "lucide-react";
import { getRuntimeConfig, VoltaApi } from "../../lib/api";

type Status = "checking" | "success" | "error";

export default function VerifyMagicLinkClient() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<Status>("checking");
  const [message, setMessage] = useState("Verifying your secure sign-in link…");

  useEffect(() => {
    let active = true;
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      setMessage("This sign-in link is missing its security token.");
      return () => { active = false; };
    }
    void (async () => {
      try {
        const config = await getRuntimeConfig();
        await new VoltaApi(config).verifyMagicLink(token);
        if (!active) return;
        setStatus("success");
        setMessage("Your private Volta workspace is now available across devices.");
      } catch (cause) {
        if (!active) return;
        setStatus("error");
        setMessage(cause instanceof Error ? cause.message : "This sign-in link is invalid or has expired.");
      }
    })();
    return () => { active = false; };
  }, [searchParams]);

  return <main className="auth-page"><section className="panel auth-card" aria-live="polite">
    <span className={`auth-icon ${status}`} aria-hidden="true">{status === "success" ? <CheckCircle2 size={24} /> : status === "error" ? <CircleAlert size={24} /> : <KeyRound size={24} />}</span>
    <p className="eyebrow">Secure sign-in</p>
    <h1>{status === "success" ? "Workspace connected" : status === "error" ? "We could not sign you in" : "Verifying your link"}</h1>
    <p>{message}</p>
    <Link className="button button-primary" href="/">{status === "success" ? "Open consultation" : "Return to Volta"}</Link>
  </section></main>;
}
