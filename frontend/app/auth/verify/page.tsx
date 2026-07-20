import { Suspense } from "react";
import VerifyMagicLinkClient from "./verify-client";

export const metadata = {
  title: "Secure sign-in | Volta Memory",
  description: "Complete passwordless sign-in for your Volta Memory workspace.",
};

export default function VerifyMagicLinkPage() {
  return <Suspense fallback={<main className="auth-page"><section className="panel auth-card"><p className="eyebrow">Secure sign-in</p><h1>Opening your secure link…</h1></section></main>}><VerifyMagicLinkClient /></Suspense>;
}
