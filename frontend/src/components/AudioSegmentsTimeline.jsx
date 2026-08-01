import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";

function toneColor(score) {
  if (score <= 20) return "#16A34A";
  if (score <= 50) return "#F59E0B";
  return "#DC2626";
}

function SegmentTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { start, end, deepfake_probability } = payload[0].payload;
  return (
    <div className="rounded-control border border-border bg-white px-3 py-2 text-xs shadow-soft">
      <p className="font-medium text-ink">
        {start}s – {end}s
      </p>
      <p className="mt-0.5 font-medium" style={{ color: toneColor(deepfake_probability) }}>
        {deepfake_probability}% deepfake probability
      </p>
    </div>
  );
}

/**
 * Renders report.segments: [{ start, end, deepfake_probability }, ...]
 * from the windowed audio pipeline (backend/services/audio_detector.py).
 * Returns null for image/video reports, or single-segment short clips
 * where a bar chart wouldn't add anything over the headline gauge.
 */
export default function AudioSegmentsTimeline({ segments }) {
  if (!segments?.length || segments.length < 2) return null;

  const data = segments.map((s) => ({
    label: `${s.start}s`,
    start: s.start,
    end: s.end,
    deepfake_probability: s.deepfake_probability,
  }));
  const flaggedCount = segments.filter((s) => s.deepfake_probability > 50).length;

  return (
    <div className="rounded-card border border-border bg-white p-6 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-base font-semibold text-ink">
          Segment-by-segment timeline
        </h3>
        <span className="text-xs text-ink-secondary">
          {segments.length} overlapping windows analyzed
          {flaggedCount > 0 && <span className="font-medium text-danger"> · {flaggedCount} flagged</span>}
        </span>
      </div>
      <p className="mt-1 text-xs text-ink-secondary">
        Audio was split into overlapping windows after silence trimming, noise reduction, and
        loudness normalization; each window was scored independently.
      </p>
      <div className="mt-4">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={{ stroke: "#E5E7EB" }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
            <Tooltip content={<SegmentTooltip />} />
            <Bar dataKey="deepfake_probability" radius={[4, 4, 0, 0]}>
              {data.map((entry, idx) => (
                <Cell key={idx} fill={toneColor(entry.deepfake_probability)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
