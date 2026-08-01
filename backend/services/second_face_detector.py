"""
Second, independently-trained face-deepfake classifier.

The reported bug — AI-generated faces predicted REAL — is exactly the
failure mode of trusting a single model's opinion outright. This module
runs a second face-deepfake Hugging Face model (model_loader.SECOND_FACE_MODEL_ID,
a different architecture/training set from the primary SigLIP2 model in
services/image_detector.py) on the same face crop. The two models rarely
share the same blind spots, so services/ensemble_engine.py gets a real
second, independent vote instead of two evaluations of the same detector.

Loaded as a soft dependency (same pattern as general_image_detector.py):
if it can't be fetched, is_available() reports False, the ensemble simply
proceeds with one fewer vote plus a warning, and nothing else breaks.
"""

import os
import logging

import cv2
import numpy as np
import torch
from PIL import Image

from services.model_loader import get_second_face_model, DEVICE

logger = logging.getLogger("truelens.second_face_detector")

_REAL_LABEL_OVERRIDE = os.getenv("SECOND_FACE_REAL_LABEL_INDEX")
_REAL_HINTS = ("real", "authentic", "human")
_FAKE_HINTS = ("fake", "deepfake", "synthetic", "generated", "ai", "gan")


def _resolve_real_label_index(id2label: dict) -> int:
    if _REAL_LABEL_OVERRIDE is not None:
        return int(_REAL_LABEL_OVERRIDE)

    for idx, label in id2label.items():
        if any(hint in label.lower() for hint in _REAL_HINTS):
            return int(idx)

    fake_idx = None
    for idx, label in id2label.items():
        if any(hint in label.lower() for hint in _FAKE_HINTS):
            fake_idx = int(idx)
    if fake_idx is not None and len(id2label) == 2:
        other = [int(i) for i in id2label if int(i) != fake_idx]
        if other:
            return other[0]

    logger.warning(
        "Could not confidently resolve the 'real' label index for the second "
        "face detector (id2label=%s). Defaulting to index 1 — verify with "
        "SECOND_FACE_REAL_LABEL_INDEX if results look inverted.",
        id2label,
    )
    return 1


def is_available() -> bool:
    model, _ = get_second_face_model()
    return model is not None


def predict_face_crop(crop_bgr: np.ndarray) -> dict:
    """
    @param crop_bgr: OpenCV BGR face crop (same crop the primary model sees).
    @returns {"prob_real": float, "available": bool}
        available=False (with prob_real=0.5, i.e. no opinion) if the model
        failed to load — the ensemble engine treats that as "this vote is
        absent", not as a confident 50/50 reading.
    """
    model, processor = get_second_face_model()
    if model is None:
        return {"prob_real": 0.5, "available": False}

    region_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(region_rgb)
    inputs = processor(images=image, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=1).squeeze()

    real_idx = _resolve_real_label_index(model.config.id2label)
    prob_real = probs[real_idx].item()
    logger.debug(
        "second face detector prob_real=%.4f (real_idx=%s, labels=%s)",
        prob_real, real_idx, model.config.id2label,
    )
    return {"prob_real": round(prob_real, 4), "available": True}
