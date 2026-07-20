import type { Metadata, Viewport } from "next";
import { DM_Serif_Display, Manrope } from "next/font/google";
import "./globals.css";
import AppHeader from "./components/AppHeader";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });
const editorial = DM_Serif_Display({ weight: "400", subsets: ["latin"], variable: "--font-editorial" });

export const metadata: Metadata = {
  title: "Volta Memory | Explainable home energy advice",
  description: "A solar consultation that remembers your home, priorities, and decisions.",
};

export const viewport: Viewport = { themeColor: "#07111F", colorScheme: "dark" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-ZA" className={`${manrope.variable} ${editorial.variable}`}>
      <body><div className="app-shell"><AppHeader /><main>{children}</main></div></body>
    </html>
  );
}
