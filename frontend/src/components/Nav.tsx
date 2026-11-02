const LINKS = ["Map", "Alerts", "Air Quality", "Stay Safe"];

export function Nav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 bg-bg">
      <div className="relative mx-auto h-[900px] w-[1440px]" style={{ height: 72 }}>
        <a href="#" className="absolute text-[24px] leading-[normal]" style={{ left: 72, top: 22 }}>
          <span className="font-bold">Wildfire</span>Risk
        </a>
        <nav className="absolute flex gap-[40px] text-[15px] leading-[normal]" style={{ right: 72, top: 27 }}>
          {LINKS.map((l) => (
            <a key={l} href="#" className="relative transition-opacity hover:opacity-100"
              style={{ opacity: l === "Map" ? 1 : 0.78 }}>
              {l}
              {l === "Map" && (
                <span className="absolute rounded-[1px] bg-ember"
                  style={{ left: -2, right: -2, top: 35, height: 2, boxShadow: "0 0 8px #F97316CC" }} />
              )}
            </a>
          ))}
        </nav>
      </div>
      <div className="h-px w-full bg-line" />
    </header>
  );
}
