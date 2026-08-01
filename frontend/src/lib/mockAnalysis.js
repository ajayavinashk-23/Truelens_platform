import { deepfakeProbabilityInterpretation } from "./utils";

// Face-aware indicator pools, kept in sync with backend/utils/report_text.py.
// Listing blink-rate/facial-boundary checks for media with no detected
// face would be misleading, so image/video each carry a "face" and
// "no_face" variant; audio has no face concept.
const VISUAL_INDICATOR_POOL = {
  image: {
    face: [
      "Facial boundary blending consistency",
      "Skin texture / noise pattern uniformity",
      "Lighting and shadow direction match",
      "Eye reflection consistency",
      "Compression artifact pattern",
    ],
    no_face: [
      "Global noise pattern uniformity",
      "Lighting and shadow direction consistency",
      "Compression artifact pattern",
      "Edge and texture consistency",
      "Color distribution naturalness",
    ],
  },
  video: {
    face: [
      "Frame-to-frame facial consistency",
      "Blink rate and eye movement naturalness",
      "Lip-sync alignment with audio",
      "Lighting consistency across frames",
      "Temporal flicker in facial region",
    ],
    no_face: [
      "Frame-to-frame scene consistency",
      "Lighting consistency across frames",
      "Compression artifact pattern across frames",
      "Temporal flicker in background regions",
      "Motion naturalness between frames",
    ],
  },
  audio: [
    "Spectral consistency across phonemes",
    "Background noise continuity",
    "Pitch and formant naturalness",
    "Breathing pattern presence",
    "Splice / concatenation artifacts",
  ],
};

const PROCESSING_TIME_RANGE = {
  image: [1.1, 2.6],
  video: [3.2, 8.4],
  audio: [1.4, 3.3],
};

function randomInRange(min, max) {
  return Math.random() * (max - min) + min;
}

function weightedDeepfakeProbability() {
  const roll = Math.random();
  if (roll < 0.5) return Number(randomInRange(2, 20).toFixed(1)); // likely authentic
  if (roll < 0.8) return Number(randomInRange(21, 50).toFixed(1)); // needs verification
  return Number(randomInRange(51, 96).toFixed(1)); // likely manipulated
}

function indicatorPool(mediaType, faceDetected) {
  const pool = VISUAL_INDICATOR_POOL[mediaType];
  if (mediaType === "audio") return pool;
  return faceDetected === false ? pool.no_face : pool.face;
}

function summaryFor(mediaType, tone, faceDetected) {
  const subject = { image: "image", video: "video", audio: "audio clip" }[mediaType];
  let text;
  if (tone === "success") {
    text = `No strong indicators of manipulation were found in this ${subject}. Feature patterns and artifact checks are consistent with authentic, unedited media.`;
  } else if (tone === "warning") {
    text = `Some signals in this ${subject} were inconclusive. The model could not confidently rule manipulation in or out — manual review is recommended before publication.`;
  } else {
    text = `Multiple heuristic checks on this ${subject} returned patterns commonly associated with synthetic or manipulated media. Treat this content as unverified.`;
  }

  if ((mediaType === "image" || mediaType === "video") && faceDetected === false) {
    text += ` No face was detected in this ${subject}, so analysis relied on whole-frame visual artifacts rather than face-specific checks.`;
  }
  return text;
}

function recommendationsFor(tone) {
  if (tone === "success") {
    return [
      "Safe to proceed with standard editorial sourcing checks.",
      "Retain the original file and this report for your records.",
    ];
  }
  if (tone === "warning") {
    return [
      "Cross-check against the original source or publisher.",
      "Have a second reviewer inspect the flagged indicators below.",
      "Avoid publishing until manual verification is complete.",
    ];
  }
  return [
    "Do not publish without independent verification.",
    "Trace the media back to its original source if possible.",
    "Escalate to a senior editor or forensic specialist.",
  ];
}

function frameAnalysisFor(mediaType, tone, deepfakeProbability) {
  if (mediaType !== "video") return undefined;

  const frameCount = Math.round(randomInRange(6, 14));
  const fakeBaseline = deepfakeProbability / 100;
  const timeline = Array.from({ length: frameCount }, (_, second) => {
    let variance = randomInRange(-0.08, 0.08);
    if (tone !== "success" && Math.random() < 0.3) {
      variance += randomInRange(0.15, 0.3);
    }
    const fake = Math.min(0.99, Math.max(0.01, fakeBaseline + variance));
    // Stored as prob_real (matches the real backend's per-frame field);
    // FrameAnalysisTimeline.jsx inverts it back to deepfake % for display.
    return { second, prob_real: Number((1 - fake).toFixed(4)) };
  });

  return { frame_count_analyzed: frameCount, timeline };
}

/**
 * Generates a mock forensics report matching the backend's JSON response shape.
 * This stands in for the real FastAPI inference endpoint if it's unreachable.
 * @param {"image"|"video"|"audio"} mediaType
 * @param {string} fileName
 */
export function generateMockReport(mediaType, fileName) {
  const deepfake_probability = weightedDeepfakeProbability();
  const { label: prediction, tone } = deepfakeProbabilityInterpretation(deepfake_probability);
  const risk_level = tone === "success" ? "Low" : tone === "warning" ? "Medium" : "High";

  // Faces are usually present in demo uploads, but occasionally simulate
  // a faceless image/video so the "no face detected" path stays visible
  // even when the backend is unreachable.
  const face_detected =
    mediaType === "image" || mediaType === "video" ? Math.random() > 0.15 : undefined;

  const [minT, maxT] = PROCESSING_TIME_RANGE[mediaType];
  const processing_time = `${randomInRange(minT, maxT).toFixed(1)} sec`;

  const pool = indicatorPool(mediaType, face_detected);
  const flagCount = tone === "success" ? 0 : tone === "warning" ? 1 : Math.ceil(randomInRange(2, 3));
  const shuffled = [...pool].sort(() => Math.random() - 0.5);
  const visual_indicators = pool.map((label) => ({
    label,
    heuristic: true,
    flagged: shuffled.slice(0, flagCount).includes(label),
  }));

  const potential_manipulation_indicators = visual_indicators
    .filter((i) => i.flagged)
    .map((i) => i.label);

  return {
    prediction,
    deepfake_probability,
    risk_level,
    processing_time,
    media_type: mediaType.charAt(0).toUpperCase() + mediaType.slice(1),
    file_name: fileName,
    timestamp: new Date().toISOString(),
    ...(face_detected !== undefined ? { face_detected } : {}),
    summary: summaryFor(mediaType, tone, face_detected),
    visual_indicators,
    potential_manipulation_indicators,
    recommendations: recommendationsFor(tone),
    ...(mediaType === "video"
      ? { frame_analysis: frameAnalysisFor(mediaType, tone, deepfake_probability) }
      : {}),
  };
}
