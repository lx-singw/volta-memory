"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun } from "lucide-react";

const navigation = [
  { href: "/", label: "Consultation" },
  { href: "/memory", label: "What Volta knows" },
  { href: "/showcase", label: "Showcase" },
];

export default function AppHeader() {
  const pathname = usePathname();
  return <header className="site-header">
    <div className="header-inner">
      <Link href="/" className="brand" aria-label="Volta Memory home"><span className="brand-mark"><Sun size={17} aria-hidden="true" /></span><strong>Volta <span>Memory</span></strong></Link>
      <nav className="site-nav" aria-label="Primary navigation">
        {navigation.map((item) => <Link key={item.href} href={item.href} className={`nav-link ${pathname === item.href ? "active" : ""}`} aria-current={pathname === item.href ? "page" : undefined}>{item.label}</Link>)}
        <Link href="/try" className={`nav-try ${pathname === "/try" ? "active" : ""}`}>Try Volta</Link>
      </nav>
    </div>
  </header>;
}
