"""
Image-quality gating and scoring, shared by the image and video pipelines.

Three jobs:
1. Reject inputs the model can't meaningfully judge (corrupted, tiny,
   extremely blurry) before wasting a GPU/CPU forward pass on them.
2. Surface quality metrics (resolution, blur, brightness, contrast) in the
   API response so the frontend can show *why* a result might be less
   reliable, instead of a bare confidence number.
3. Feed a single 0-1 "quality_score" into utils/trust_score.py so
   confidence calibration can discount low-quality inputs rather than
   reporting raw model probability as if it were equally trustworthy for
   every upload.

All thresholds here are heuristics, not calibrated against a labeled
quality dataset. They're deliberately conservative (reject only clearly
unusable input) so we don't false-positive-reject legitimate photos.
"""

import cv2
import numpy as np

MIN_WIDTH = 32
MIN_HEIGHT = 32

# Laplacian variance below this = essentially unusable (heavy motion blur /
# out-of-focus / near-solid-color). Below the warn threshold but above the
# reject threshold, we still run inference but attach a warning and dock
# the quality score.
BLUR_REJECT_THRESHOLD = 8.0
BLUR_WARN_THRESHOLD = 40.0

# Mean pixel brightness (0-255). Outside this band the image is likely
# over/under-exposed enough to hurt the model's judgment.
BRIGHTNESS_WARN_LOW = 25.0
BRIGHTNESS_WARN_HIGH = 235.0

# Std-dev of pixel intensities. Very low contrast means a mostly flat/
# featureless image (fog, blown-out sky, solid background).
CONTRAST_WARN_THRESHOLD = 15.0


def compute_blur_score(gray: np.ndarray) -> float:
    """Variance of the Laplacian. Higher = sharper. This is the standard
    cheap focus-measure operator (no ground truth needed, no extra model)."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def compute_brightness(gray: np.ndarray) -> float:
    return float(gray.mean())


def compute_contrast(gray: np.ndarray) -> float:
    return float(gray.std())


def _score_component(value: float, low_warn: float, high_warn=None, invert=False) -> float:
    """Maps a raw metric to a 0-1 sub-score used inside the composite
    quality score. `invert=True` means higher raw value == worse (used for
    blur, where we pass 1/blur-ish behavior via the caller instead)."""
    if high_warn is not None:
        # Value should sit between low_warn and high_warn; score decays
        # linearly outside that band.
        if low_warn <= value <= high_warn:
            return 1.0
        distance = min(abs(value - low_warn), abs(value - high_warn))
        return max(0.0, 1.0 - distance / max(low_warn, 1.0))
    if invert:
        return max(0.0, min(1.0, value / low_warn))
    return max(0.0, min(1.0, 1.0 - value / max(low_warn, 1.0)))


def assess_image_quality(frame_bgr: np.ndarray) -> dict:
    """
    @param frame_bgr: HxWx3 OpenCV BGR array (already successfully decoded)
    @returns {
        "width": int, "height": int,
        "blur_score": float, "brightness": float, "contrast": float,
        "quality_score": float (0-100),
        "warnings": [str, ...],
        "reject": bool, "reject_reason": str|None,
    }
    """
    height, width = frame_bgr.shape[:2]
    warnings = []
    reject_reason = None

    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return {
            "width": width,
            "height": height,
            "blur_score": 0.0,
            "brightness": 0.0,
            "contrast": 0.0,
            "quality_score": 0.0,
            "warnings": ["Image resolution is too small to analyze reliably."],
            "reject": True,
            "reject_reason": (
                f"Image is only {width}x{height}px; minimum supported size is "
                f"{MIN_WIDTH}x{MIN_HEIGHT}px."
            ),
        }

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blur_score = compute_blur_score(gray)
    brightness = compute_brightness(gray)
    contrast = compute_contrast(gray)

    if blur_score < BLUR_REJECT_THRESHOLD:
        return {
            "width": width,
            "height": height,
            "blur_score": round(blur_score, 2),
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "quality_score": 0.0,
            "warnings": ["Image is extremely blurry and cannot be analyzed reliably."],
            "reject": True,
            "reject_reason": (
                f"Blur score {blur_score:.1f} is below the minimum usable "
                f"threshold ({BLUR_REJECT_THRESHOLD})."
            ),
        }

    if blur_score < BLUR_WARN_THRESHOLD:
        warnings.append("Image is noticeably blurry — results may be less reliable.")
    if brightness < BRIGHTNESS_WARN_LOW:
        warnings.append("Image is very dark (underexposed) — results may be less reliable.")
    elif brightness > BRIGHTNESS_WARN_HIGH:
        warnings.append("Image is overexposed / blown out — results may be less reliable.")
    if contrast < CONTRAST_WARN_THRESHOLD:
        warnings.append("Image has very low contrast — results may be less reliable.")
    if max(width, height) < 200:
        warnings.append("Image resolution is low — results may be less reliable.")

    blur_sub = min(1.0, blur_score / (BLUR_WARN_THRESHOLD * 3))
    brightness_sub = _score_component(brightness, BRIGHTNESS_WARN_LOW, BRIGHTNESS_WARN_HIGH)
    contrast_sub = min(1.0, contrast / (CONTRAST_WARN_THRESHOLD * 3))
    resolution_sub = min(1.0, (width * height) / (400 * 400))

    quality_score = (
        0.40 * blur_sub + 0.25 * brightness_sub + 0.20 * contrast_sub + 0.15 * resolution_sub
    ) * 100

    return {
        "width": width,
        "height": height,
        "blur_score": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "quality_score": round(quality_score, 1),
        "warnings": warnings,
        "reject": False,
        "reject_reason": None,
    }


def enhance_contrast(frame_bgr: np.ndarray) -> np.ndarray:
    """CLAHE (contrast-limited adaptive histogram equalization) on the L
    channel of LAB color space. Applied to face crops before inference —
    helps the classifier on low-contrast / poorly-lit face regions without
    distorting color, which a naive global histogram equalization would."""
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)
    merged = cv2.merge((l_enhanced, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
