"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Icon, type IconName } from "@/components/Icon";
import { PageShell, Skeleton, Waking, ErrorNote, useApi, ease } from "@/components/ui";

type Item = { id: number; hazard: string; stage: string; audience: string; title: string; body: string; source_url: string | null };

const HAZARDS = [{ k: "wildfire", l: "Wildfire", i: "flame" as IconName }, { k: "air_quality", l: "Smoke & bad air", i: "wind" as IconName }];
const STAGES = [{ k: "before", l: "Before" }, { k: "during", l: "During" }, { k: "after", l: "After" }];
const AUD: Record<string, string> = { general_public: "Everyone", rural_farming: "Farmers & villages", children_elderly: "Children & elderly" };

export default function StaySafePage() {
  const [hazard, setHazard] = useState("wildfire");
  const [stage, setStage] = useState("before");
  useEffect(() => {
    const s = new URLSearchParams(window.location.search).get("stage");
    if (s && STAGES.some((x) => x.k === s)) setStage(s);
  }, []);
  const q = useApi<Item[]>(`/preparedness?hazard=${hazard}`);
  const items = (q.data ?? []).filter((i) => i.stage === stage);

  return (
    <PageShell active="Stay Safe" eyebrow="Stay safe" title="What to do, step by step"
      sub="Simple steps from India's National Disaster Management Authority (NDMA). Pick the danger and when.">
      <div className="flex flex-wrap gap-3">
        {HAZARDS.map((h) => (
          <button key={h.k} onClick={() => setHazard(h.k)}
            className={`flex h-[48px] items-center gap-2 rounded-[24px] border px-5 text-[16px] transition ${h.k === hazard ? "border-ember bg-ember/15" : "border-line text-muted hover:text-white"}`}>
            <Icon name={h.i} size={18} color={h.k === hazard ? "#F97316" : "#9AA3B2"} />{h.l}
          </button>
        ))}
      </div>
      <div className="mt-6 flex w-full max-w-[368px] rounded-[16px] border border-line bg-surface p-1">
        {STAGES.map((s) => (
          <button key={s.k} onClick={() => setStage(s.k)} className="relative h-[44px] flex-1 text-[15px]">
            {s.k === stage && <motion.span layoutId="stage" className="absolute inset-0 rounded-[12px] bg-ember" transition={{ duration: 0.4, ease }} />}
            <span className="relative">{s.l}</span>
          </button>
        ))}
      </div>

      <div className="mt-10">
        {q.loading && <><Waking /><div className="grid gap-6 md:grid-cols-2"><Skeleton h={200} /><Skeleton h={200} /></div></>}
        {q.error && <ErrorNote what="safety steps" />}
        {q.data && (
          <AnimatePresence mode="wait">
            <motion.div key={`${hazard}-${stage}`} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.4, ease }}
              className="grid gap-6 md:grid-cols-2">
              {items.length === 0 ? <p className="text-muted">No steps for this yet.</p> : items.map((it) => (
                <article key={it.id} className="rounded-[16px] border border-line bg-surface p-7">
                  <p className="text-[13px] font-semibold uppercase tracking-[0.12em] text-ember">{AUD[it.audience] ?? it.audience}</p>
                  <h2 className="mt-3 text-[22px] font-semibold leading-[30px]">{it.title}</h2>
                  <p className="mt-3 text-[16px] leading-[26px] text-muted">{it.body}</p>
                  {it.source_url && <a href={it.source_url} target="_blank" rel="noreferrer" className="mt-5 inline-block text-[14px] text-white/80 underline-offset-4 hover:underline">Source: NDMA</a>}
                </article>
              ))}
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      <div className="mt-14 rounded-[16px] border border-[#EF4444]/50 bg-[#EF4444]/10 p-7">
        <h2 className="text-[22px] font-semibold">In an emergency</h2>
        <p className="mt-2 text-[16px] leading-[26px] text-white/85">Call <b>112</b> (national emergency) or <b>101</b> (fire). Follow instructions from local authorities.</p>
      </div>
    </PageShell>
  );
}
