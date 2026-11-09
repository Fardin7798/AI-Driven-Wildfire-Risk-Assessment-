"use client";
import { animate, useInView } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { fmt } from "@/lib/api";

export function CountUp({ to, suffix = "", duration = 1.6 }: { to: number | null; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!inView || to == null) return;
    const c = animate(0, to, { duration, ease: [0.16, 1, 0.3, 1], onUpdate: (x) => setV(Math.round(x)) });
    return () => c.stop();
  }, [inView, to, duration]);
  return <span ref={ref}>{to == null ? "–" : fmt(v) + suffix}</span>;
}
