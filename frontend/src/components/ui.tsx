"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { getJSON } from "@/lib/api";

export const ease = [0.16, 1, 0.3, 1] as const;
export const DISCLAIMER = "Academic decision-support tool only; not an official warning. Consult IMD, CPCB, NDMA, and local authorities.";

/** Fetch a backend path; null path = skip. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState(false);
  const [notFound, setNotFound] = useState(false);
  useEffect(() => {
    if (!path) return;
    let alive = true; setData(null); setError(false); setNotFound(false);
    getJSON<T>(path).then((d) => alive && setData(d)).catch((e: Error) => {
      if (!alive) return;
      setError(true); setNotFound(String(e?.message ?? "").startsWith("404 "));
    });
    return () => { alive = false; };
  }, [path]);
  return { data, error, notFound, loading: !!path && !data && !error };
}

export function PageShell({ active, eyebrow, title, sub, children }: {
  active: string; eyebrow?: string; title: React.ReactNode; sub?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <main className="min-h-screen">
      <Nav active={active} />
      <div className="mx-auto w-full max-w-[1296px] px-6 pb-24 pt-[120px] md:px-[72px]">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease }}>
          {eyebrow && <p className="text-[13px] font-semibold uppercase tracking-[0.14em] text-ember">{eyebrow}</p>}
          <h1 className="mt-3 text-[40px] font-bold leading-[1.1] md:text-[56px]">{title}</h1>
          {sub && <p className="mt-4 max-w-[720px] text-[18px] leading-[28px] text-muted">{sub}</p>}
        </motion.div>
        <div className="mt-12">{children}</div>
        <p className="mt-20 border-t border-line pt-6 text-[13px] leading-[20px] text-muted">{DISCLAIMER}</p>
      </div>
    </main>
  );
}

export function Card({ children, className = "", i = 0 }: { children: React.ReactNode; className?: string; i?: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.6, ease, delay: 0.06 * i }}
      className={`rounded-[16px] border border-line bg-surface p-6 ${className}`}>
      {children}
    </motion.div>
  );
}

export function Skeleton({ h = 120, className = "" }: { h?: number; className?: string }) {
  return <div className={`animate-pulse rounded-[16px] bg-white/5 ${className}`} style={{ height: h }} />;
}

export function Waking() {
  return <p className="mb-6 inline-block rounded-full border border-line bg-surface px-4 py-2 text-[13px] text-muted">Loading live data… (server may take ~30s to wake)</p>;
}

export function ErrorNote({ what = "this data" }: { what?: string }) {
  return <p className="rounded-[16px] border border-line bg-surface px-6 py-5 text-[15px] text-muted">Couldn&apos;t load {what} right now. Please refresh in a minute.</p>;
}

export function Badge({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex h-[32px] items-center rounded-[16px] px-[14px] text-[13px] font-semibold"
      style={{ color, background: `${color}24`, border: `1px solid ${color}E6` }}>{children}</span>
  );
}
