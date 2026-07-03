export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, background: "#0f172a", color: "#e2e8f0" }}>
        <header style={{ padding: "1rem 1.5rem", borderBottom: "1px solid #334155" }}>
          <strong>Volta Memory</strong>
          <nav style={{ display: "inline-flex", gap: "1rem", marginLeft: "1.5rem" }}>
            <a href="/" style={{ color: "#93c5fd" }}>Chat</a>
            <a href="/memory" style={{ color: "#93c5fd" }}>Memory view</a>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
