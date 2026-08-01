import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

const COLORS = { Low: "#16A34A", Medium: "#F59E0B", High: "#DC2626" };

export default function RiskDistributionChart({ history }) {
  const counts = { Low: 0, Medium: 0, High: 0 };
  history.forEach((entry) => {
    if (counts[entry.risk_level] !== undefined) counts[entry.risk_level] += 1;
  });
  const data = Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <p className="flex h-[200px] items-center justify-center text-sm text-ink-secondary">
        No session history yet.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={45}
          outerRadius={72}
          paddingAngle={3}
        >
          {data.map((entry) => (
            <Cell key={entry.name} fill={COLORS[entry.name]} stroke="none" />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: "1px solid #E5E7EB",
            fontSize: 12,
          }}
        />
        <Legend
          verticalAlign="bottom"
          height={24}
          iconType="circle"
          wrapperStyle={{ fontSize: 12, color: "#6B7280" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
