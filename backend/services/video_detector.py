"""
Scene-aware video authenticity pipeline.

Replaces plain "grab one frame per second" sampling with:
  1. Uniform candidate sampling at a fine interval (a few frames/sec).
  2. Scene-change / duplicate-frame filtering: consecutive candidates whose
     color-histogram correlation is very high are near-duplicates and are
     skipped, so we don't burn inference budget re-analyzing a static
     shot dozens of times, and we do capture frames right after a cut or
     a fast-changing (potentially manipulated) region.
  3. Quality gating: blurry/empty (near-solid-color) frames are skipped —
     they're not analyzable and would just add noise to the aggregate.
  4. Per-frame hybrid routing (services/image_detector.route_and_predict_frame):
     face(s) present -> SigLIP2 face model; no face -> general AI-image
     detector. Each frame is routed independently, since a video can
     legitimately contain both face and non-face shots.
  5. Aggregation into an overall verdict, a per-second confidence timeline,
     and the list of timestamps flagged as suspicious (deepfake
     probability > 50).
"""

import logging
import os
import tempfile

import cv2
import numpy as np

from services.image_detector import route_and_predict_frame
from utils.image_quality import compute_blur_score, BLUR_REJECT_THRESHOLD

logger = logging.getLogger("truelens.video_detector")

CANDIDATE_FPS = 2.0        # how densely we sample candidate frames before filtering
MAX_FRAMES_ANALYZED = 40   # hard cap on frames actually run through a model
DUPLICATE_HIST_CORR_THRESHOLD = 0.985  # >= this correlation to prior kept frame = duplicate
BLUR_SKIP_THRESHOLD = BLUR_REJECT_THRESHOLD * 2  # slightly stricter than the single-image reject bar


def _frame_histogram(frame_bgr):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist


def predict_video_bytes(video_bytes: bytes, max_frames: int = MAX_FRAMES_ANALYZED) -> dict:
    """
    @returns {
        "prob_real_avg": float,
        "frame_count_analyzed": int,
        "frames_skipped": int,
        "face_detected": bool,          # True if a face was found in >=50% of analyzed frames
        "face_detected_ratio": float,
        "timeline": [{"second": float, "prob_real": float, "pipeline_used": str}, ...],
        "suspicious_timestamps": [float, ...],
        "warnings": [str, ...],
    }
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    timeline = []
    face_flags = []
    warnings = []
    frames_skipped = 0
    prev_hist = None

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file — it may be corrupted or in an unsupported format.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps if fps and fps > 0 else 25.0
        candidate_interval = max(int(round(fps / CANDIDATE_FPS)), 1)

        frame_index = 0
        while len(timeline) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_index % candidate_interval != 0:
                frame_index += 1
                continue
            frame_index += 1
            second = round(frame_index / fps, 2)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur_score = compute_blur_score(gray)
            if blur_score < BLUR_SKIP_THRESHOLD:
                frames_skipped += 1
                continue

            hist = _frame_histogram(frame)
            if prev_hist is not None:
                correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                if correlation >= DUPLICATE_HIST_CORR_THRESHOLD:
                    frames_skipped += 1
                    continue
            prev_hist = hist

            result = route_and_predict_frame(frame, explain=False)
            deepfake_probability = round((1 - result["prob_real"]) * 100, 1)
            timeline.append(
                {
                    "second": second,
                    "prob_real": round(result["prob_real"], 4),
                    "deepfake_probability": deepfake_probability,
                    "pipeline_used": result["pipeline_used"],
                    "face_count": result["face_count"],
                }
            )
            face_flags.append(result["face_detected"])
            warnings.extend(w for w in result["warnings"] if w not in warnings)

        cap.release()
    finally:
        os.unlink(tmp_path)

    if not timeline:
        raise ValueError(
            "No usable frames could be extracted from this video — it may be too short, too "
            "blurry, or entirely static/duplicate frames."
        )

    prob_real_avg = sum(t["prob_real"] for t in timeline) / len(timeline)
    face_detected_ratio = sum(face_flags) / len(face_flags) if face_flags else 0.0
    suspicious_timestamps = [t["second"] for t in timeline if t["deepfake_probability"] > 50]

    total_candidates = len(timeline) + frames_skipped
    valid_ratio = len(timeline) / total_candidates if total_candidates else 1.0
    if valid_ratio < 0.3:
        warnings.append(
            "Most sampled frames were skipped as blurry or duplicate — analyzed on a smaller "
            "sample than usual, treat the result with extra caution."
        )

    logger.info(
        "video frames_analyzed=%d frames_skipped=%d prob_real_avg=%.4f",
        len(timeline), frames_skipped, prob_real_avg,
    )

    return {
        "prob_real_avg": prob_real_avg,
        "frame_count_analyzed": len(timeline),
        "frames_skipped": frames_skipped,
        "face_detected": face_detected_ratio >= 0.5,
        "face_detected_ratio": round(face_detected_ratio, 3),
        "timeline": timeline,
        "suspicious_timestamps": suspicious_timestamps,
        "warnings": warnings,
        "valid_ratio": round(valid_ratio, 3),
    }
