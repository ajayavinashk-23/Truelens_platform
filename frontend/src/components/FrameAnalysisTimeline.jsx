import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  Dot,
} from "recharts";

// Same tiers as the single deepfake-probability metric: 0-20 authentic,
// 21-50 needs review, 51-100 manipulated. Higher = more likely fake.
function toneColor(score) {
  if (score <= 20) return "#16A34A";
  if (score <= 50) return "#F59E0B";
  return "#DC2626";
}

function FrameDot({ cx, cy, payload }) {
  return (
    <Dot
      cx={cx}
      cy={cy}
      r={4}
      fill={toneColor(payload.deepfakeProbability)}
      stroke="#FFFFFF"
      strokeWidth={1.5}
    />
  );
}

function FrameTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { second, deepfakeProbability } = payload[0].payload;
  return (
    <div className="rounded-control border border-border bg-white px-3 py-2 text-xs shadow-soft">
      <p className="font-medium text-ink">Frame @ {second}s</p>
      <p className="mt-0.5 font-medium" style={{ color: toneColor(deepfakeProbability) }}>
        {deepfakeProbability}% deepfake probability
      </p>
    </div>
  );
}

/**
 * Renders the video pipeline's per-frame prediction over time
 * (report.frame_analysis.timeline: [{ second, prob_real }, ...]).
 * prob_real is the raw model output; this component inverts it to the
 * same deepfake-probability direction as the headline gauge so the chart
 * reads consistently with the rest of the report.
 * Returns null for image/audio reports, or if the backend didn't include it.
 */
export default function FrameAnalysisTimeline({ frameAnalysis }) {
  if (!frameAnalysis?.timeline?.length) return null;

  const data = frameAnalysis.timeline.map((t) => ({
    second: t.second,
    deepfakeProbability: Math.round((1 - t.prob_real) * 100),
  }));
  const flaggedCount = data.filter((d) => d.deepfakeProbability > 50).length;

  return (
    <div className="rounded-card border border-border bg-white p-6 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-display text-base font-semibold text-ink">
          Frame analysis timeline
        </h3>
        <span className="text-xs text-ink-secondary">
          {frameAnalysis.frame_count_analyzed ?? data.length} frames sampled
          {flaggedCount > 0 && (
            <span className="font-medium text-danger"> · {flaggedCount} flagged</span>
          )}
        </span>
      </div>
      <p className="mt-1 text-xs text-ink-secondary">
        Per-frame deepfake probability from the pretrained model, sampled roughly once per second.
      </p>

      <div className="mt-4">
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="frameFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0F766E" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#0F766E" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis
              dataKey="second"
              tickFormatter={(s) => `${s}s`}
              tick={{ fontSize: 11, fill: "#6B7280" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: "#6B7280" }}
              axisLine={false}
              tickLine={false}
            />
            <ReferenceLine y={20} stroke="#16A34A" strokeOpacity={0.35} strokeDasharray="4 4" />
            <ReferenceLine y={50} stroke="#F59E0B" strokeOpacity={0.35} strokeDasharray="4 4" />
            <Tooltip content={<FrameTooltip />} />
            <Area type="monotone" dataKey="deepfakeProbability" stroke="none" fill="url(#frameFill)" />
            <Line
              type="monotone"
              dataKey="deepfakeProbability"
              stroke="#0F766E"
              strokeWidth={2}
              dot={<FrameDot />}
              activeDot={{ r: 5 }}
              isAnimationActive={true}
              animationDuration={500}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
