import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2 } from "lucide-react";
import { PIPELINE_STEPS } from "../lib/pipelineSteps";

/**
 * @param {number} currentStepIndex - steps before this index are complete,
 *   this index is actively running, steps after are not yet revealed.
 */
export default function PipelineSteps({ currentStepIndex }) {
  const visibleSteps = PIPELINE_STEPS.slice(0, currentStepIndex + 1);

  return (
    <div className="rounded-card border border-border bg-white p-6 shadow-soft">
      <h2 className="font-display text-base font-semibold text-ink">
        Running detection pipeline
      </h2>
      <p className="mt-1 text-sm text-ink-secondary">
        Each stage completes before the next begins.
      </p>

      <ul className="mt-5 space-y-3">
        <AnimatePresence initial={false}>
          {visibleSteps.map((label, i) => {
            const isComplete = i < currentStepIndex;
            const isActive = i === currentStepIndex;
            return (
              <motion.li
                key={label}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="flex items-center gap-3 text-sm"
              >
                {isComplete ? (
                  <motion.span
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    className="flex h-5 w-5 shrink-0 items-center justify-center text-success"
                  >
                    <CheckCircle2 size={18} />
                  </motion.span>
                ) : isActive ? (
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center text-accent-700">
                    <Loader2 size={16} className="animate-spin" />
                  </span>
                ) : null}
                <span
                  className={
                    isComplete || isActive
                      ? "font-medium text-ink"
                      : "text-ink-secondary"
                  }
                >
                  {label}
                </span>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>
    </div>
  );
}
