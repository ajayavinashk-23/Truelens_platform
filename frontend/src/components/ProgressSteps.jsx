import { Check } from "lucide-react";
import { cn } from "../lib/utils";

const STAGES = ["Select", "Upload", "Analyze & report"];

/**
 * @param {number} current - 1-indexed current stage (1, 2, or 3)
 */
export default function ProgressSteps({ current }) {
  return (
    <ol className="flex items-center gap-2">
      {STAGES.map((stage, i) => {
        const step = i + 1;
        const isComplete = step < current;
        const isActive = step === current;
        return (
          <li key={stage} className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold transition-colors duration-200",
                isComplete && "bg-accent-700 text-white",
                isActive && "bg-accent-50 text-accent-700 ring-2 ring-accent-700",
                !isComplete && !isActive && "bg-surface-secondary text-ink-secondary"
              )}
            >
              {isComplete ? <Check size={13} /> : step}
            </div>
            <span
              className={cn(
                "text-sm font-medium",
                isActive ? "text-ink" : "text-ink-secondary"
              )}
            >
              {stage}
            </span>
            {step < STAGES.length && (
              <span className="mx-1 h-px w-8 bg-border" aria-hidden="true" />
            )}
          </li>
        );
      })}
    </ol>
  );
}
