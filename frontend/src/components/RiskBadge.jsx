const STYLES = {
  Low: "bg-success/10 text-success",
  Medium: "bg-warning/10 text-warning",
  High: "bg-danger/10 text-danger",
};

export default function RiskBadge({ level }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
        STYLES[level] ?? "bg-surface-secondary text-ink-secondary"
      }`}
    >
      {level} risk
    </span>
  );
}
