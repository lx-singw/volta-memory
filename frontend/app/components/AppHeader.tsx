"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun } from "lucide-react";

export default function AppHeader() {
  const pathname = usePathname();
  return (
    <header className="site-header">
      <div className="header-inner">
        <Link href="/" className="brand" aria-label="Volta Memory home">
          <span className="brand-mark"><Sun size={17} aria-hidden="true" /></span>
          <strong>Volta <span>Memory</span></strong>
        </Link>
        <nav className="site-nav" aria-label="Primary navigation">
          <Link href="/" className={`nav-link ${pathname === "/" ? "active" : ""}`} aria-current={pathname === "/" ? "page" : undefined}>Consultation</Link>
          <Link href="/memory" className={`nav-link ${pathname === "/memory" ? "active" : ""}`} aria-current={pathname === "/memory" ? "page" : undefined}>What Volta knows</Link>
        </nav>
      </div>
    </header>
  );
}
