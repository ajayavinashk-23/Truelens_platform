import { motion, animate } from "framer-motion";
import { useEffect, useState } from "react";
import { deepfakeProbabilityInterpretation } from "../lib/utils";

const TONE_COLORS = {
  success: "#16A34A",
  warning: "#F59E0B",
  danger: "#DC2626",
};

/**
 * Circular gauge for a 0-100 deepfake probability score. Higher = more
 * likely AI-generated/manipulated (color runs green -> amber -> red as
 * the score climbs, opposite of a "trust" gauge).
 *
 * Motion: ring fill 900ms ease-out, 150ms delay, on mount/score change.
 * The number counts up over the same 900ms/ease-out/150ms-delay window
 * so the two read as one animation rather than a static label next to a
 * moving ring.
 *
 * @param {number} score
 * @param {number} size - px
 * @param {string} label
 */
export default function TrustGauge({ score, size = 120, label = "Deepfake probability" }) {
  const radius = (size - 14) / 2;
  const circumference = 2 * Math.PI * radius;
  const { label: interpretation, tone } = deepfakeProbabilityInterpretation(score);
  const color = TONE_COLORS[tone];

  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    const controls = animate(0, score, {
      duration: 0.9,
      delay: 0.15,
      ease: "easeOut",
      onUpdate: (v) => setDisplayScore(Math.round(v)),
    });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [score]);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#E5E7EB"
            strokeWidth={9}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={9}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{
              strokeDashoffset: circumference - (score / 100) * circumference,
            }}
            transition={{ duration: 0.9, ease: "easeOut", delay: 0.15 }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-2xl font-bold text-ink">
            {displayScore}
            <span className="text-base font-semibold">%</span>
          </span>
        </div>
      </div>
      <div className="text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-secondary">
          {label}
        </p>
        <p className="text-sm font-semibold" style={{ color }}>
          {interpretation}
        </p>
      </div>
    </div>
  );
}
