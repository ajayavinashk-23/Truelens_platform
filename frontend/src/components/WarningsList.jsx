import { AlertTriangle } from "lucide-react";

/**
 * Renders report.warnings (array of plain-text strings from the backend —
 * e.g. "Image is noticeably blurry", "General AI image detector is
 * unavailable, falling back..."). Returns null if there are none, so
 * it's safe to always mount from the report panel.
 */
export default function WarningsList({ warnings }) {
  if (!warnings?.length) return null;

  return (
    <div className="rounded-card border border-warning/30 bg-warning/5 p-5">
      <div className="flex items-center gap-2">
        <AlertTriangle size={16} className="text-warning" />
        <h3 className="font-display text-sm font-semibold text-ink">
          Warnings ({warnings.length})
        </h3>
      </div>
      <ul className="mt-2.5 space-y-1.5">
        {warnings.map((warning) => (
          <li key={warning} className="flex gap-2 text-xs text-ink-secondary">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-warning" />
            {warning}
          </li>
        ))}
      </ul>
    </div>
  );
}
