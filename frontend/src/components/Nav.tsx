const LINKS = [
  { l: "Map", href: "/map" },
  { l: "Alerts", href: "/alerts" },
  { l: "Air Quality", href: "/air-quality" },
  { l: "Stay Safe", href: "/stay-safe" },
  { l: "About", href: "/about" },
];

export function Nav({ active = "Map" }: { active?: string }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 bg-bg">
      <div className="relative mx-auto h-[72px] w-[1440px] max-w-full">
        <a href="/" className="absolute text-[24px] leading-[normal]" style={{ left: 72, top: 22 }}>
          <span className="font-bold">Wildfire</span>Risk
        </a>
        <nav className="absolute flex gap-[40px] text-[15px] leading-[normal]" style={{ right: 72, top: 27 }}>
          {LINKS.map(({ l, href }) => (
            <a key={l} href={href} className="relative transition-opacity hover:opacity-100" style={{ opacity: l === active ? 1 : 0.78 }}>
              {l}
              {l === active && (
                <span className="absolute rounded-[1px] bg-ember" style={{ left: -2, right: -2, top: 35, height: 2, boxShadow: "0 0 8px #F97316CC" }} />
              )}
            </a>
          ))}
        </nav>
      </div>
      <div className="h-px w-full bg-line" />
    </header>
  );
}
