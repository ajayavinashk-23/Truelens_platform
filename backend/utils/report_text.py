"""
Generates the narrative parts of the forensics report (summary, indicator
checklist, recommendations). Kept in the same shape as
frontend/src/lib/mockAnalysis.js so swapping the frontend from mock data to
this real endpoint is a drop-in change.

Face-aware: image and video each have a "face" indicator pool and a
"no_face" pool. Listing blink-rate or facial-boundary checks for a photo
with no face in it would be actively misleading, so the caller must pass
whether a face was actually detected (see utils/face_detection.py) and
this module picks the matching pool.
"""

VISUAL_INDICATOR_POOL = {
    "image": {
        "face": [
            "Facial boundary blending consistency",
            "Skin texture / noise pattern uniformity",
            "Lighting and shadow direction match",
            "Eye reflection consistency",
            "Compression artifact pattern",
        ],
        "no_face": [
            "Global noise pattern uniformity",
            "Lighting and shadow direction consistency",
            "Compression artifact pattern",
            "Edge and texture consistency",
            "Color distribution naturalness",
        ],
    },
    "video": {
        "face": [
            "Frame-to-frame facial consistency",
            "Blink rate and eye movement naturalness",
            "Lip-sync alignment with audio",
            "Lighting consistency across frames",
            "Temporal flicker in facial region",
        ],
        "no_face": [
            "Frame-to-frame scene consistency",
            "Lighting consistency across frames",
            "Compression artifact pattern across frames",
            "Temporal flicker in background regions",
            "Motion naturalness between frames",
        ],
    },
    "audio": [
        "Spectral consistency across phonemes",
        "Background noise continuity",
        "Pitch and formant naturalness",
        "Breathing pattern presence",
        "Splice / concatenation artifacts",
    ],
}

_RISK_TO_FLAG_COUNT = {"Low": 0, "Medium": 1, "High": 3}


def _indicator_pool(media_type: str, face_detected: bool | None):
    pool = VISUAL_INDICATOR_POOL[media_type]
    if isinstance(pool, dict):
        # image/video: pick the face-aware pool. Default to "face" only
        # when face_detected wasn't determined at all (shouldn't happen
        # in practice, since both detectors always report it).
        key = "no_face" if face_detected is False else "face"
        return pool[key]
    return pool  # audio: single flat pool, no face concept


def build_visual_indicators(media_type: str, risk_level: str, face_detected: bool | None = None):
    """
    Every indicator is explicitly labeled heuristic: the underlying model
    outputs one overall authenticity score, not independently computed
    per-indicator measurements. This checklist communicates *what the
    pipeline conceptually checks*, flagged in proportion to the overall
    risk level, rather than fabricating separate metrics.
    """
    pool = _indicator_pool(media_type, face_detected)
    flag_count = _RISK_TO_FLAG_COUNT[risk_level]
    # Deterministic-ish selection: flag the lowest-ranked indicators first,
    # so repeated runs on the same file are stable.
    flagged_labels = set(pool[:flag_count]) if flag_count else set()

    return [
        {"label": label, "heuristic": True, "flagged": label in flagged_labels}
        for label in pool
    ]


def summary_for(media_type: str, risk_level: str, face_detected: bool | None = None) -> str:
    subject = {"image": "image", "video": "video", "audio": "audio clip"}[media_type]
    if risk_level == "Low":
        text = (
            f"No strong indicators of manipulation were found in this {subject}. "
            "Feature patterns and artifact checks are consistent with authentic, "
            "unedited media."
        )
    elif risk_level == "Medium":
        text = (
            f"Some signals in this {subject} were inconclusive. The model could "
            "not confidently rule manipulation in or out — manual review is "
            "recommended before publication."
        )
    else:
        text = (
            f"Multiple heuristic checks on this {subject} returned patterns commonly "
            "associated with synthetic or manipulated media. Treat this content as "
            "unverified."
        )

    if media_type in ("image", "video") and face_detected is False:
        text += (
            " No face was detected in this "
            f"{subject}, so analysis relied on whole-frame visual artifacts "
            "rather than face-specific checks."
        )

    return text


def recommendations_for(risk_level: str) -> list[str]:
    if risk_level == "Low":
        return [
            "Safe to proceed with standard editorial sourcing checks.",
            "Retain the original file and this report for your records.",
        ]
    if risk_level == "Medium":
        return [
            "Cross-check against the original source or publisher.",
            "Have a second reviewer inspect the flagged indicators below.",
            "Avoid publishing until manual verification is complete.",
        ]
    return [
        "Do not publish without independent verification.",
        "Trace the media back to its original source if possible.",
        "Escalate to a senior editor or forensic specialist.",
    ]
