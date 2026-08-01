import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const TONE_COLOR = { Low: "#16A34A", Medium: "#F59E0B", High: "#DC2626" };

export default function DetectionHistoryChart({ history }) {
  if (history.length === 0) {
    return (
      <p className="flex h-[200px] items-center justify-center text-sm text-ink-secondary">
        No session history yet.
      </p>
    );
  }

  // oldest -> newest, last 10
  const data = [...history]
    .slice(0, 10)
    .reverse()
    .map((entry, i) => ({
      name: `#${i + 1}`,
      deepfake_probability: entry.deepfake_probability,
      risk_level: entry.risk_level,
    }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
        <XAxis
          dataKey="name"
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
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: "1px solid #E5E7EB",
            fontSize: 12,
          }}
        />
        <Bar dataKey="deepfake_probability" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={TONE_COLOR[entry.risk_level] ?? "#0F766E"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
