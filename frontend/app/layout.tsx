import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { UserMenu } from "./components/UserMenu";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SCAAR — Clasificación de Actos Reclamados",
  description:
    "Clasificador de actos reclamados (adjetivo / sustantivo) con log de razonamiento jurídico inmutable.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <div className="flex items-baseline gap-6">
              <Link href="/" className="text-base font-semibold tracking-tight">
                SCAAR
              </Link>
              <nav className="flex gap-4 text-sm text-slate-600">
                <Link href="/casos" className="hover:text-slate-900">
                  Casos
                </Link>
                <Link href="/clasificar" className="hover:text-slate-900">
                  Clasificar
                </Link>
                <Link href="/corpus" className="hover:text-slate-900">
                  Corpus
                </Link>
                <Link href="/modelo" className="hover:text-slate-900">
                  Modelo
                </Link>
              </nav>
            </div>
            <UserMenu />
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
