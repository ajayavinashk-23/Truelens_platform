import { useState } from "react";
import { Layers } from "lucide-react";

const TABS = [
  { key: "overlay", label: "Overlay" },
  { key: "heatmap", label: "Heatmap" },
];

/**
 * Grad-CAM style explainability viewer. Expects report.heatmap and
 * report.heatmap_overlay to be data-URI PNGs (see
 * backend/services/gradcam.py + routers/image.py). Renders nothing if
 * the backend couldn't produce a heatmap for this image (unsupported
 * architecture, etc) — a missing heatmap never blocks the rest of the
 * report from rendering.
 */
export default function HeatmapPanel({ heatmap, overlay }) {
  const [tab, setTab] = useState("overlay");
  if (!heatmap && !overlay) return null;

  const src = tab === "overlay" ? overlay ?? heatmap : heatmap ?? overlay;

  return (
    <div className="rounded-card border border-border bg-white p-6 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Layers size={16} className="text-accent-700" />
          <h3 className="font-display text-base font-semibold text-ink">
            Explainability heatmap
          </h3>
        </div>
        <div className="flex gap-1 rounded-full bg-surface-secondary p-0.5 text-xs">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`rounded-full px-3 py-1 font-medium transition-colors ${
                tab === t.key ? "bg-white text-ink shadow-soft" : "text-ink-secondary"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-1 text-xs text-ink-secondary">
        Highlights which regions of the image most influenced the model's prediction.
      </p>
      <div className="mt-4 flex justify-center rounded-control bg-ink p-2">
        <img src={src} alt="Prediction heatmap" className="max-h-[360px] rounded-control object-contain" />
      </div>
    </div>
  );
}
