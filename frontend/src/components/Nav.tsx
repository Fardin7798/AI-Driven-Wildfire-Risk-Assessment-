"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

const LINKS = [
  { l: "Map", href: "/map" },
  { l: "Alerts", href: "/alerts" },
  { l: "Air Quality", href: "/air-quality" },
  { l: "Stay Safe", href: "/stay-safe" },
  { l: "About", href: "/about" },
];

export function Nav({ active = "Map" }: { active?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <header className="fixed inset-x-0 top-0 z-50 bg-bg">
      <div className="relative mx-auto h-[72px] w-[1440px] max-w-full">
        <a href="/" className="absolute left-[20px] top-[22px] text-[22px] leading-[normal] md:left-[72px] md:text-[24px]">
          <span className="font-bold">Wildfire</span>Risk
        </a>

        {/* Desktop links */}
        <nav className="absolute hidden gap-[40px] text-[15px] leading-[normal] md:flex" style={{ right: 72, top: 27 }}>
          {LINKS.map(({ l, href }) => (
            <a key={l} href={href} className="relative transition-opacity hover:opacity-100" style={{ opacity: l === active ? 1 : 0.78 }}>
              {l}
              {l === active && (
                <span className="absolute rounded-[1px] bg-ember" style={{ left: -2, right: -2, top: 35, height: 2, boxShadow: "0 0 8px #F97316CC" }} />
              )}
            </a>
          ))}
        </nav>

        {/* Mobile menu button */}
        <button aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen((o) => !o)}
          className="absolute right-[12px] top-[14px] flex h-[44px] w-[44px] items-center justify-center rounded-[12px] hover:bg-white/5 md:hidden">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round">
            {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </div>
      <div className="h-px w-full bg-line" />

      <AnimatePresence>
        {open && (
          <motion.nav initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}
            className="border-b border-line bg-bg px-[12px] pb-[12px] pt-[4px] md:hidden">
            {LINKS.map(({ l, href }) => (
              <a key={l} href={href}
                className={`flex h-[52px] items-center rounded-[12px] px-[12px] text-[17px] ${l === active ? "bg-white/5 font-semibold text-ember" : "text-white/85"}`}>
                {l}
              </a>
            ))}
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
