import clsx from "clsx";

/**
 * Merge conditional class names.
 * @param  {...any} inputs
 * @returns {string}
 */
export function cn(...inputs) {
  return clsx(...inputs);
}

/**
 * Format a 0-100 deepfake probability into its tier interpretation.
 * Higher = more likely AI-generated/manipulated.
 *
 * Thresholds must match backend/utils/trust_score.py::interpret_deepfake_probability
 * — kept at 12/45 (previously 20/50) so a borderline AI-generated face
 * doesn't clear the "Likely Authentic" bar as easily.
 * @param {number} probability
 * @returns {{ label: string, tone: "success" | "warning" | "danger" }}
 */
export function deepfakeProbabilityInterpretation(probability) {
  if (probability <= 12) return { label: "Likely Authentic", tone: "success" };
  if (probability <= 45) return { label: "Needs Manual Verification", tone: "warning" };
  return { label: "Likely Manipulated", tone: "danger" };
}
