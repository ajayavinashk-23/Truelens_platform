import { motion } from "framer-motion";

const STEPS = [
  {
    n: "01",
    title: "Select & upload",
    body: "Choose image, video, or audio and upload the file you want verified.",
  },
  {
    n: "02",
    title: "Detection engine runs",
    body: "The pipeline extracts features, compares against learned patterns, and checks visual or acoustic artifacts step by step.",
  },
  {
    n: "03",
    title: "Review the forensics report",
    body: "See prediction, deepfake probability, and risk level side-by-side with your original media.",
  },
  {
    n: "04",
    title: "Export & share",
    body: "Download a structured JSON report for your investigation or newsroom workflow.",
  },
];

export default function StepTimeline() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {STEPS.map((step, i) => (
        <motion.div
          key={step.n}
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.25, ease: "easeOut", delay: i * 0.05 }}
          className="flex gap-4 rounded-card border border-border bg-white p-6 shadow-soft"
        >
          <span className="font-display text-2xl font-bold text-accent-700/25">
            {step.n}
          </span>
          <div>
            <h3 className="font-display text-base font-semibold text-ink">
              {step.title}
            </h3>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-secondary">
              {step.body}
            </p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
