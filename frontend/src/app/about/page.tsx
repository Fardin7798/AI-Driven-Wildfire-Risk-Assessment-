"use client";

import { Icon, type IconName } from "@/components/Icon";
import { PageShell, Card, Skeleton, Waking, ErrorNote, useApi } from "@/components/ui";
import { fmt, RISK_COLORS } from "@/lib/api";

type Model = {
  model_type: string; version: string; trained_at: string | null; status: string;
  metrics: { test_year?: number; roc_auc?: number; pr_auc?: number; precision?: number; recall?: number; f1_score?: number; train_samples?: number; test_samples?: number } | null;
  feature_list: string[]; thresholds: Record<string, number>;
};
type Sources = { sources: { name: string; category: string; license: string; url: string }[] };
type Disclaimer = { disclaimer: string; academic_mandate: string; official_authorities: string[] };

const STEPS: { t: string; d: string; i: IconName }[] = [
  { t: "Satellites spot fires", d: "NASA FIRMS reports hot spots over India several times a day.", i: "flame" },
  { t: "Weather is added", d: "Daily heat, humidity, wind and rain for every district (Open-Meteo), turned into fire-weather indices.", i: "wind" },
  { t: "The model predicts", d: "An XGBoost model gives each of India's districts a chance of wildfire for today.", i: "search" },
  { t: "We explain why", d: "SHAP picks the top 3 reasons behind each forecast, shown in plain words.", i: "shield-house" },
];
const pct = (v?: number) => (v == null ? "–" : `${Math.round(v * 100)}%`);

export default function AboutPage() {
  const models = useApi<Model[]>("/models/current");
  const src = useApi<Sources>("/meta/sources");
  const disc = useApi<Disclaimer>("/meta/disclaimer");
  const wf = models.data?.find((m) => m.model_type === "wildfire");
  const m = wf?.metrics;

  return (
    <PageShell active="About" eyebrow="About the model" title="How WildfireRisk works"
      sub="A final-year B.Tech project that turns satellite and weather data into a daily wildfire forecast for every district in India.">
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {STEPS.map((s, j) => (
          <Card key={s.t} i={j}>
            <div className="flex items-center gap-3">
              <span className="flex h-[36px] w-[36px] items-center justify-center rounded-full bg-ember/15 text-[15px] font-bold text-ember">{j + 1}</span>
              <Icon name={s.i} size={20} color="#9AA3B2" />
            </div>
            <h2 className="mt-5 text-[20px] font-semibold">{s.t}</h2>
            <p className="mt-2 text-[15px] leading-[24px] text-muted">{s.d}</p>
          </Card>
        ))}
      </div>

      <h2 className="mt-16 text-[28px] font-semibold">How good is it?</h2>
      {models.loading && <div className="mt-4"><Waking /></div>}
      {models.error && <div className="mt-4"><ErrorNote what="model details" /></div>}
      {!m ? !models.error && <Skeleton h={160} className="mt-6" /> : (
        <>
          <p className="mt-2 text-[15px] text-muted">Tested on {m.test_year ?? "unseen"} data the model never saw while learning. Model {wf!.version}.</p>
          <div className="mt-6 grid grid-cols-2 gap-6 md:grid-cols-4">
            {[
              { l: "Catches real fire days", v: pct(m.recall), s: "recall" },
              { l: "Alarms that were right", v: pct(m.precision), s: "precision" },
              { l: "Overall ranking skill", v: m.roc_auc?.toFixed(2) ?? "–", s: "ROC-AUC (1.0 = perfect)" },
              { l: "Balance score", v: m.f1_score?.toFixed(2) ?? "–", s: "F1" },
            ].map((t, j) => (
              <Card key={t.s} i={j}>
                <p className="text-[15px] text-muted">{t.l}</p>
                <p className="mt-3 text-[44px] font-bold leading-none text-ember">{t.v}</p>
                <p className="mt-3 text-[13px] text-muted">{t.s}</p>
              </Card>
            ))}
          </div>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <Card>
              <h3 className="text-[20px] font-semibold">Risk levels</h3>
              <div className="mt-4 space-y-3 text-[15px]">
                {[["Low", 0, wf!.thresholds.moderate], ["Moderate", wf!.thresholds.moderate, wf!.thresholds.high], ["High", wf!.thresholds.high, wf!.thresholds.extreme], ["Extreme", wf!.thresholds.extreme, 1]].map(([c, a, b]) => (
                  <p key={c as string} className="flex items-center gap-3">
                    <span className="h-[10px] w-[10px] rounded-full" style={{ background: RISK_COLORS[c as string] }} />
                    <span className="w-[96px]">{c}</span>
                    <span className="text-muted">{pct(a as number)} to {pct(b as number)} chance</span>
                  </p>
                ))}
              </div>
            </Card>
            <Card>
              <h3 className="text-[20px] font-semibold">Trained on</h3>
              <p className="mt-4 text-[44px] font-bold leading-none">{m.train_samples ? fmt(m.train_samples) : "–"}</p>
              <p className="mt-2 text-[15px] text-muted">district-days, using {wf!.feature_list.length} inputs (weather, dryness, season, location, past fires).</p>
            </Card>
          </div>
        </>
      )}

      <h2 className="mt-16 text-[28px] font-semibold">Data sources</h2>
      {src.error ? <div className="mt-4"><ErrorNote what="sources" /></div> : !src.data ? <Skeleton h={200} className="mt-6" /> : (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {src.data.sources.map((s, j) => (
            <Card key={s.name} i={j} className="!p-5">
              <a href={s.url} target="_blank" rel="noreferrer" className="text-[17px] font-semibold hover:text-ember">{s.name}</a>
              <p className="mt-1 text-[14px] text-muted">{s.category}</p>
              <p className="mt-2 text-[12px] text-muted/80">{s.license}</p>
            </Card>
          ))}
        </div>
      )}

      {disc.data && (
        <Card className="mt-16">
          <h2 className="text-[22px] font-semibold">Important</h2>
          <p className="mt-3 text-[15px] leading-[26px] text-muted">{disc.data.academic_mandate}</p>
          <p className="mt-4 text-[15px] text-white/85">For official warnings, follow: {disc.data.official_authorities.slice(0, 4).join(", ")}.</p>
        </Card>
      )}
    </PageShell>
  );
}
