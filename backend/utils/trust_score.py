"""
Converts a model's "probability the media is real" into the headline
metrics the product shows: deepfake_probability (0-100, higher = more
likely AI-generated/manipulated) and a separately-calibrated confidence
score.

This module previously exposed two separate numbers (trust_score +
confidence) that were near-redundant, then collapsed to one
deepfake_probability. This version reintroduces a distinct "confidence"
number, but calibrated rather than derived purely from model probability:
confidence answers "how much should you trust this particular number?",
factoring in input quality (blur/brightness/contrast for images, valid
frame ratio for video, audio quality for audio), not just how far the
model's raw probability sits from the 50/50 midpoint. A crisp, high-
quality face crop that the model is unsure about and a blurry, tiny image
the model is unsure about should NOT be reported with the same confidence.

Kept in one place so image/video/audio detectors stay consistent with
each other and with the frontend's tier definitions (see
frontend/src/lib/utils.js -> deepfakeProbabilityInterpretation).
"""


def interpret_deepfake_probability(deepfake_probability: float):
    """
    0-12   -> Likely Authentic / Low risk
    13-45  -> Needs Manual Verification / Medium risk
    46-100 -> Likely Manipulated / High risk

    Previously 0-20 / 21-50 / 51-100. The reported bug (many AI-generated
    faces predicted REAL) meant the model only needed ~80% confidence in
    "real" to clear the bar for a confident authentic verdict — too low a
    bar for a single, occasionally-wrong model. Narrowing the "authentic"
    band to <=12 requires a stronger confident-real signal before making
    that claim, and widens "Needs Manual Verification" so borderline
    generated faces the model is only mildly confident about land there
    instead of being cleared as real.
    """
    if deepfake_probability <= 12:
        return "Likely Authentic", "Low"
    if deepfake_probability <= 45:
        return "Needs Manual Verification", "Medium"
    return "Likely Manipulated", "High"


def calibrate_confidence(deepfake_probability: float, quality_factor: float = 1.0) -> float:
    """
    @param deepfake_probability: 0-100
    @param quality_factor: 0-1, a composite of input-quality signals
        (image quality_score/100, blur score normalized, fraction of
        valid/analyzed frames, number of faces successfully read, audio
        quality after VAD/noise reduction, etc). Callers build this from
        whatever signals they have; 1.0 means "no quality discount".
    @returns 0-100 confidence: how much weight to put on the prediction,
        distinct from the prediction's direction/magnitude itself.
    """
    quality_factor = max(0.0, min(1.0, quality_factor))
    # Distance from the maximally-uncertain midpoint (50) is the model's
    # own signal of how sure it is; scale that into a 50-100 base range,
    # then discount by input quality. A perfect-quality input where the
    # model is maximally uncertain still gets confidence=50 (not 0) —
    # "confidence" here means "trust in the number", and a genuinely
    # ambiguous 50/50 read from clean input is itself a meaningful,
    # trustworthy result.
    distance = abs(deepfake_probability - 50) / 50.0  # 0..1
    base_confidence = 50 + distance * 50  # 50..100
    calibrated = 50 + (base_confidence - 50) * quality_factor
    return round(max(0.0, min(100.0, calibrated)), 1)


def build_report_fields(prob_real: float, media_type: str, quality_factor: float = 1.0):
    """
    @param prob_real: model's probability the media is authentic, 0-1
    @param media_type: "Image" | "Video" | "Audio"
    @param quality_factor: 0-1 composite input-quality signal, see
        calibrate_confidence(). Defaults to 1.0 (no discount) for callers
        that haven't been updated to pass it, so this stays backward
        compatible.
    @returns dict with prediction, deepfake_probability, confidence,
        risk_level, media_type
    """
    deepfake_probability = round((1 - prob_real) * 100, 1)
    prediction, risk_level = interpret_deepfake_probability(deepfake_probability)
    confidence = calibrate_confidence(deepfake_probability, quality_factor)

    return {
        "prediction": prediction,
        "deepfake_probability": deepfake_probability,
        "confidence": confidence,
        "risk_level": risk_level,
        "media_type": media_type,
    }
