import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";
import AppHeader from "./components/AppHeader";

export const metadata: Metadata = {
  title: "Volta Memory | Explainable home energy advice",
  description: "A solar consultation that remembers your home, priorities, and decisions.",
};

export const viewport: Viewport = { themeColor: "#07111F", colorScheme: "dark" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-ZA">
      <body>
        <Script src="/runtime-config.js" strategy="beforeInteractive" />
        <div className="app-shell"><AppHeader /><main>{children}</main></div>
      </body>
    </html>
  );
}
