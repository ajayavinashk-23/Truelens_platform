import { motion } from "framer-motion";
import { CheckCircle2, Clock } from "lucide-react";
import TrustGauge from "./TrustGauge";

const CORNER_POSITIONS = [
  "top-3 left-3 border-t-2 border-l-2",
  "top-3 right-3 border-t-2 border-r-2",
  "bottom-3 left-3 border-b-2 border-l-2",
  "bottom-3 right-3 border-b-2 border-r-2",
];

export default function HeroPreviewCard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut", delay: 0.1 }}
      className="w-full max-w-md overflow-hidden rounded-card border border-border bg-white shadow-softLg"
    >
      {/* Media preview area with scan animation */}
      <div className="relative h-48 overflow-hidden bg-ink">
        <div className="absolute inset-0 bg-gradient-to-br from-ink via-[#1F2937] to-ink" />

        {/* Corner brackets */}
        {CORNER_POSITIONS.map((pos, i) => (
          <div
            key={i}
            className={`pointer-events-none absolute h-6 w-6 border-accent-200/70 ${pos}`}
          />
        ))}

        {/* Face bounding box with pulse */}
        <motion.div
          className="absolute left-1/2 top-1/2 h-20 w-16 -translate-x-1/2 -translate-y-1/2 rounded-lg border-2 border-accent-200"
          animate={{ scale: [1, 1.03, 1], opacity: [0.85, 1, 0.85] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Scan line */}
        <motion.div
          className="absolute inset-x-0 h-px bg-accent-200/80"
          style={{ boxShadow: "0 0 8px 1px rgba(153,246,228,0.6)" }}
          animate={{ top: ["8%", "92%", "8%"] }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        />

        <div className="absolute bottom-2 left-3 flex items-center gap-1.5 rounded-full bg-black/40 px-2.5 py-1 text-[11px] font-medium text-white backdrop-blur-sm">
          <span className="h-1.5 w-1.5 animate-pulseSoft rounded-full bg-accent-200" />
          Analyzing frame 14 / 30
        </div>
      </div>

      {/* Report summary */}
      <div className="flex items-center gap-5 p-5">
        <TrustGauge score={8} size={92} />
        <div className="flex-1 space-y-2.5">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 size={15} className="text-success" />
            <span className="text-ink-secondary">Prediction</span>
            <span className="ml-auto font-semibold text-ink">
              Likely Authentic
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock size={15} className="text-ink-secondary" />
            <span className="text-ink-secondary">Processed in</span>
            <span className="ml-auto font-semibold text-ink">1.8s</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
