"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";

const MapExplorer = dynamic(() => import("@/components/map/MapExplorer"), { ssr: false });

export default function MapPage() {
  const [params, setParams] = useState<{ d?: number; q?: string; bare: boolean } | null>(null);
  useEffect(() => {
    const u = new URLSearchParams(window.location.search);
    setParams({ d: u.get("d") ? Number(u.get("d")) : undefined, q: u.get("q") || undefined, bare: u.has("bare") });
  }, []);
  return (
    <main className="fixed inset-0">
      <Nav active="Map" />
      <div className="absolute inset-x-0 bottom-0 top-0">
        {params && <MapExplorer initialId={params.d} initialQuery={params.q} bare={params.bare} />}
      </div>
    </main>
  );
}
