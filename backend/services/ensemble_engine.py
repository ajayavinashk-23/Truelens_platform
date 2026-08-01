"""
Ensemble decision engine.

Combines every independent detector's opinion into a single verdict
instead of ever letting one model or one heuristic decide alone — this is
the direct fix for the reported bug (AI-generated faces predicted REAL by
a single trusted classifier).

Every contributing signal is expressed the same way: a DetectorSignal with
a "prob_real" in [0, 1] and a relative weight. combine():
  1. Renormalizes weights over whichever signals are actually available
     (a model that failed to load simply drops out, it doesn't silently
     count as a confident vote).
  2. Computes the weighted-average prob_real.
  3. Measures disagreement (spread between the highest and lowest available
     prob_real). Large disagreement means the blended number, whatever it
     comes out to, isn't trustworthy on its own — the verdict is forced to
     SUSPICIOUS and the returned prob_real is clamped into a neutral band,
     rather than reporting a confident REAL/FAKE that one dissenting
     detector would have contradicted.
"""

from dataclasses import dataclass, field


@dataclass
class DetectorSignal:
    name: str
    prob_real: float               # 0-1, this detector's own opinion
    weight: float                  # relative weight before renormalization
    available: bool = True
    extra: dict = field(default_factory=dict)  # raw scores/visuals for the API response


# Spread (max prob_real - min prob_real) among available signals above this
# means the detectors meaningfully disagree -> force SUSPICIOUS rather than
# trust whatever the weighted average happens to land on.
DISAGREEMENT_SUSPICIOUS_THRESHOLD = 0.45

REAL_THRESHOLD = 0.62
FAKE_THRESHOLD = 0.38

# When disagreement forces SUSPICIOUS, clamp the reported prob_real into
# this band so downstream confidence calibration (utils/trust_score.py)
# reads it as "inconclusive", never as a confident REAL or FAKE number.
_SUSPICIOUS_CLAMP_LOW = 0.56
_SUSPICIOUS_CLAMP_HIGH = 0.86


def combine(signals: list) -> dict:
    """
    @param signals: list[DetectorSignal]
    @returns {
        "prob_real": float,
        "verdict": "REAL" | "FAKE" | "SUSPICIOUS",
        "disagreement": float,
        "artifact_scores": {name: prob_real, ...},
        "weights_used": {name: normalized_weight, ...},
        "models_used": [name, ...],
        "unavailable": [name, ...],
    }
    """
    available = [s for s in signals if s.available]
    unavailable = [s.name for s in signals if not s.available]

    if not available:
        return {
            "prob_real": 0.5,
            "verdict": "SUSPICIOUS",
            "disagreement": 0.0,
            "artifact_scores": {},
            "weights_used": {},
            "models_used": [],
            "unavailable": unavailable,
        }

    total_weight = sum(s.weight for s in available) or 1.0
    weighted_sum = sum(s.prob_real * s.weight for s in available)
    prob_real = weighted_sum / total_weight

    probs = [s.prob_real for s in available]
    disagreement = max(probs) - min(probs)

    if disagreement > DISAGREEMENT_SUSPICIOUS_THRESHOLD:
        verdict = "SUSPICIOUS"
        prob_real = min(max(prob_real, _SUSPICIOUS_CLAMP_LOW), _SUSPICIOUS_CLAMP_HIGH)
    elif prob_real >= REAL_THRESHOLD:
        verdict = "REAL"
    elif prob_real <= FAKE_THRESHOLD:
        verdict = "FAKE"
    else:
        verdict = "SUSPICIOUS"

    return {
        "prob_real": round(prob_real, 4),
        "verdict": verdict,
        "disagreement": round(disagreement, 4),
        "artifact_scores": {s.name: round(s.prob_real, 4) for s in available},
        "weights_used": {s.name: round(s.weight / total_weight, 4) for s in available},
        "models_used": [s.name for s in available],
        "unavailable": unavailable,
    }
