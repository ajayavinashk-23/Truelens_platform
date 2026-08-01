import { ScanEye } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-surface-secondary">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-10 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-control bg-accent-700 text-white">
            <ScanEye size={16} strokeWidth={2.25} />
          </span>
          <span className="font-display text-sm font-bold text-ink">
            Truelens
          </span>
        </div>
        <p className="text-sm text-ink-secondary">
          Built for a hackathon prototype. Forensic outputs are heuristic
          signals, not legal or scientific certification of authenticity.
        </p>
      </div>
    </footer>
  );
}
