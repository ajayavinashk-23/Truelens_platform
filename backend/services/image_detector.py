"""
Hybrid image-authenticity pipeline.

Flow (see routers/image.py for the HTTP layer):
  1. Decode + validate quality (utils/image_quality.py). Corrupted,
     too-tiny, or unusably blurry uploads are rejected before any model
     runs.
  2. Detect faces (utils/face_detection.py, MediaPipe with Haar fallback).
  3. NO FACE  -> general (non-face) AI-image detector
                 (services/general_image_detector.py), covering
                 landscapes/art/animals/buildings/products/screenshots/etc.
     FACE(S)  -> SigLIP2 face-deepfake model (this module), run
                 independently on every detected face after CLAHE
                 contrast enhancement, then aggregated.
  4. Grad-CAM explainability (services/gradcam.py) on whichever
     image/crop actually went through the model.

`route_and_predict_frame` is the shared core also used by
services/video_detector.py so a single video frame is routed exactly the
same way a standalone image upload would be.
"""

import logging
import os

import cv2
import numpy as np
import torch
from PIL import Image

from services.model_loader import get_image_model, DEVICE
from services.general_image_detector import predict_frame_bgr as predict_general_frame
from services.general_image_detector import is_available as general_detector_available
from services.second_face_detector import predict_face_crop as predict_second_face_crop
from services.second_face_detector import is_available as second_face_available
from services.gradcam import generate_gradcam
from services.ensemble_engine import DetectorSignal, combine as ensemble_combine
from utils.face_detection import detect_all_faces
from utils.image_quality import assess_image_quality, enhance_contrast
from utils.frequency_analysis import compute_frequency_artifact_score
from utils.ela_analysis import compute_ela
from utils.noise_analysis import compute_noise_score

logger = logging.getLogger("truelens.image_detector")

_REAL_LABEL_OVERRIDE = os.getenv("IMAGE_REAL_LABEL_INDEX")

# The face-deepfake model (SigLIP2) previously decided the verdict alone.
# This was the root cause of the reported bug: many AI-generated
# (especially diffusion-generated) faces were predicted REAL because
# nothing cross-checked the model's softmax output. Every face crop is now
# scored by five independent signals and combined by
# services/ensemble_engine.py's weighted voting — no single model/signal
# fully controls the result, and strong disagreement between them yields
# SUSPICIOUS instead of a falsely-confident REAL or FAKE.
#
# Weights sum to 1.0. The two trained classifiers get the most weight since
# they're the highest-precision signals; the three deterministic heuristics
# (frequency/ELA/noise) are kept modest since they're supporting evidence,
# not trained classifiers, per the same reasoning the old FREQ_WEIGHT
# comment used to make.
SIGLIP_WEIGHT = 0.35
SECOND_FACE_WEIGHT = 0.30
FREQ_WEIGHT = 0.15
ELA_WEIGHT = 0.12
NOISE_WEIGHT = 0.08


def _resolve_real_label_index(id2label: dict) -> int:
    """
    Find whichever class index corresponds to "real"/"authentic".

    For the currently configured model this is index 1 (documented as
    {"0": "fake", "1": "real"}). IMAGE_REAL_LABEL_INDEX is kept as an
    override in case a future model swap turns out to have an inverted
    config — set it if scripts/check_image_label_mapping.py flags a
    mismatch.
    """
    if _REAL_LABEL_OVERRIDE is not None:
        return int(_REAL_LABEL_OVERRIDE)

    for idx, label in id2label.items():
        if "real" in label.lower() or "authentic" in label.lower():
            return int(idx)
    return 1


def _predict_face_crop(crop_bgr: np.ndarray, model, processor, real_idx: int) -> tuple:
    """
    Runs every independent face-authenticity signal on one face crop and
    combines them through the ensemble engine.

    @returns (ensemble_result: dict, pil_image_for_gradcam: PIL.Image,
              siglip_prob_real: float, freq: dict, ela: dict, noise: dict)
        ensemble_result is services.ensemble_engine.combine()'s output —
        prob_real / verdict / disagreement / artifact_scores / etc.
    """
    enhanced = enhance_contrast(crop_bgr)
    region_rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(region_rgb)
    inputs = processor(images=image, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=1).squeeze()

    siglip_prob_real = probs[real_idx].item()

    # Second, independently-trained face-deepfake model (different
    # architecture/training data — see services/second_face_detector.py).
    second_face = predict_second_face_crop(crop_bgr)

    # Three deterministic, model-free heuristics — all computed on the
    # original crop (not the CLAHE-enhanced one), since contrast
    # enhancement can itself distort the frequency/noise/compression
    # signatures these are trying to read.
    freq = compute_frequency_artifact_score(crop_bgr)
    ela = compute_ela(crop_bgr)
    noise = compute_noise_score(crop_bgr)

    signals = [
        DetectorSignal("siglip2_face_model", siglip_prob_real, SIGLIP_WEIGHT, available=True),
        DetectorSignal(
            "second_face_model", second_face["prob_real"], SECOND_FACE_WEIGHT,
            available=second_face["available"],
        ),
        DetectorSignal("frequency_analysis", freq["prob_real_freq"], FREQ_WEIGHT, available=True),
        DetectorSignal("error_level_analysis", ela["prob_real_ela"], ELA_WEIGHT, available=True),
        DetectorSignal("noise_residual_analysis", noise["prob_real_noise"], NOISE_WEIGHT, available=True),
    ]
    ensemble_result = ensemble_combine(signals)

    return ensemble_result, image, siglip_prob_real, freq, ela, noise


def route_and_predict_frame(frame_bgr: np.ndarray, explain: bool = False) -> dict:
    """
    Core hybrid routing logic, reusable for a standalone image or a single
    sampled video frame.

    @returns {
        "prob_real": float,                # aggregated, used for the headline score
        "verdict": "REAL" | "FAKE" | "SUSPICIOUS",
        "pipeline_used": "face_deepfake_detector" | "general_ai_image_detector" | "face_deepfake_detector_fallback",
        "face_detected": bool,
        "face_count": int,
        "faces": [{"prob_real": float, "box": [x,y,w,h], "confidence": float|None, "verdict": str,
                    "artifact_scores": {...}}, ...],
        "artifact_scores": {detector_name: prob_real, ...},   # for the worst/driving face or the no-face pipeline
        "models_used": [str, ...],
        "disagreement": float,
        "warnings": [str, ...],
        "explanation_image": {"original", "heatmap", "overlay", "top_region"} | None,
        "ela_heatmap": str|None,
    }
    """
    warnings = []
    faces = detect_all_faces(frame_bgr)

    if faces:
        model, processor = get_image_model()
        real_idx = _resolve_real_label_index(model.config.id2label)

        if not second_face_available():
            warnings.append(
                "The second, independent face-deepfake model is unavailable; this result relies on the "
                "primary model plus frequency/ELA/noise heuristics only, with reduced ensemble coverage."
            )

        face_results = []
        for face in faces:
            ensemble_result, pil_crop, siglip_prob_real, freq, ela, noise = _predict_face_crop(
                face["crop"], model, processor, real_idx
            )
            face_results.append(
                {
                    "prob_real": ensemble_result["prob_real"],
                    "verdict": ensemble_result["verdict"],
                    "box": list(face["box"]),
                    "confidence": face["confidence"],
                    "siglip_prob_real": round(siglip_prob_real, 4),
                    "disagreement": ensemble_result["disagreement"],
                    "artifact_scores": ensemble_result["artifact_scores"],
                    "frequency_anomaly_score": freq["anomaly_score"],
                    "ela_manipulation_score": ela["manipulation_score"],
                    "noise_anomaly_score": noise["noise_score"],
                }
            )
            face["_pil_crop"] = pil_crop
            face["_ela_heatmap"] = ela["heatmap_data_uri"]
            face["_ensemble"] = ensemble_result

        # Aggregate: the most suspicious face drives the overall verdict —
        # a single convincingly-faked face in a group photo shouldn't be
        # diluted into "probably fine" by averaging with unmanipulated
        # faces standing next to it. We still report every face's own
        # score in "faces" so the caller/UI isn't hiding that detail.
        worst = min(face_results, key=lambda f: f["prob_real"])
        prob_real_overall = worst["prob_real"]
        worst_index = face_results.index(worst)
        driving_ensemble = faces[worst_index]["_ensemble"]

        if worst["verdict"] == "SUSPICIOUS" and worst["disagreement"] > 0:
            warnings.append(
                "The independent detectors disagreed significantly on this face (spread="
                f"{worst['disagreement']:.2f}); the result was reported as SUSPICIOUS rather than a "
                "confidently forced REAL or FAKE."
            )
        if driving_ensemble["unavailable"]:
            warnings.append(
                "Unavailable detectors for this face: " + ", ".join(driving_ensemble["unavailable"]) + "."
            )

        explanation_image = None
        if explain:
            explanation_image = generate_gradcam(
                model, processor, faces[worst_index]["_pil_crop"], real_idx, DEVICE
            )

        return {
            "prob_real": prob_real_overall,
            "verdict": worst["verdict"],
            "pipeline_used": "face_deepfake_detector",
            "face_detected": True,
            "face_count": len(faces),
            "faces": face_results,
            "artifact_scores": worst["artifact_scores"],
            "models_used": driving_ensemble["models_used"],
            "disagreement": worst["disagreement"],
            "warnings": warnings,
            "explanation_image": explanation_image,
            "ela_heatmap": faces[worst_index]["_ela_heatmap"],
        }

    # No face -> general AI-image detector, combined with the same
    # deterministic heuristics through the ensemble engine (never let the
    # general classifier decide alone either).
    general_result = predict_general_frame(frame_bgr)
    freq = compute_frequency_artifact_score(frame_bgr)
    ela = compute_ela(frame_bgr)
    noise = compute_noise_score(frame_bgr)

    if not general_result["available"]:
        warnings.append(
            "General (non-face) AI image detector is unavailable; falling back to the "
            "face-deepfake model on the full frame, which is not tuned for non-face subjects."
        )
        model, processor = get_image_model()
        real_idx = _resolve_real_label_index(model.config.id2label)
        ensemble_result, pil_full, _siglip, _freq, _ela, _noise = _predict_face_crop(
            frame_bgr, model, processor, real_idx
        )
        explanation_image = generate_gradcam(model, processor, pil_full, real_idx, DEVICE) if explain else None
        pipeline_used = "face_deepfake_detector_fallback"
    else:
        # General image classifier gets the dominant weight (it's the
        # trained model tuned for this subject matter); the three
        # heuristics vote alongside it exactly as they do for faces.
        signals = [
            DetectorSignal("general_ai_image_detector", general_result["prob_real"], 0.55, available=True),
            DetectorSignal("frequency_analysis", freq["prob_real_freq"], 0.20, available=True),
            DetectorSignal("error_level_analysis", ela["prob_real_ela"], 0.15, available=True),
            DetectorSignal("noise_residual_analysis", noise["prob_real_noise"], 0.10, available=True),
        ]
        ensemble_result = ensemble_combine(signals)

        explanation_image = None
        if explain and general_detector_available():
            from services.model_loader import get_general_image_model
            gmodel, gprocessor = get_general_image_model()
            gimage_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil_full = Image.fromarray(gimage_rgb)
            from services.general_image_detector import _resolve_real_label_index as _resolve_general_idx
            real_idx = _resolve_general_idx(gmodel.config.id2label)
            explanation_image = generate_gradcam(gmodel, gprocessor, pil_full, real_idx, DEVICE)
        pipeline_used = "general_ai_image_detector"

    prob_real = ensemble_result["prob_real"]
    if ensemble_result["verdict"] == "SUSPICIOUS" and ensemble_result["disagreement"] > 0:
        warnings.append(
            "The independent detectors disagreed significantly (spread="
            f"{ensemble_result['disagreement']:.2f}); the result was reported as SUSPICIOUS rather than a "
            "confidently forced REAL or FAKE."
        )

    return {
        "prob_real": prob_real,
        "verdict": ensemble_result["verdict"],
        "pipeline_used": pipeline_used,
        "face_detected": False,
        "face_count": 0,
        "faces": [],
        "artifact_scores": ensemble_result["artifact_scores"],
        "models_used": ensemble_result["models_used"],
        "disagreement": ensemble_result["disagreement"],
        "warnings": warnings,
        "explanation_image": explanation_image,
        "ela_heatmap": ela["heatmap_data_uri"],
    }


def build_explanation_text(result: dict, quality: dict, deepfake_probability: float) -> str:
    pipeline = result["pipeline_used"]
    region = None
    if result.get("explanation_image"):
        region = result["explanation_image"].get("top_region")

    if pipeline.startswith("face"):
        subject = "facial" if result["face_count"] <= 1 else f"the most suspicious of {result['face_count']} detected faces'"
        if deepfake_probability > 50:
            base = f"High deepfake probability — {subject} texture, blending, and lighting-consistency patterns matched known synthetic/face-swap signatures."
            if region:
                base += f" The model's attention was concentrated in the {region} of the face."
        elif deepfake_probability > 20:
            base = f"Some {subject} patterns were inconclusive; the model could not confidently separate authentic texture noise from synthetic artifacts."
        else:
            base = f"Low deepfake probability — {subject} texture and lighting consistency were in line with authentic, unedited faces."
    else:
        if deepfake_probability > 50:
            base = "No face was detected. The general AI-image detector identified synthetic texture, color, and compression patterns commonly seen in AI-generated imagery."
            if region:
                base += f" The strongest signal came from the {region} of the image."
        elif deepfake_probability > 20:
            base = "No face was detected. The general AI-image detector's signal was inconclusive for this subject."
        else:
            base = "No face was detected. The general AI-image detector found texture and noise patterns consistent with an authentic (non-AI-generated) photo."

    if quality["warnings"]:
        base += " Note: " + " ".join(quality["warnings"])

    return base


def predict_image_bytes(image_bytes: bytes) -> dict:
    """
    @returns a rich dict consumed by routers/image.py — see that module
        for the exact HTTP response shape. Raises ValueError for
        corrupted/rejected input (routers turn this into a 4xx/5xx).
    """
    file_bytes = np.frombuffer(image_bytes, dtype=np.uint8)
    frame_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if frame_bgr is None:
        raise ValueError("Could not decode the uploaded image — it may be corrupted or in an unsupported format.")

    quality = assess_image_quality(frame_bgr)
    if quality["reject"]:
        raise ValueError(quality["reject_reason"])

    result = route_and_predict_frame(frame_bgr, explain=True)

    deepfake_probability = round((1 - result["prob_real"]) * 100, 1)
    explanation = build_explanation_text(result, quality, deepfake_probability)

    quality_factor = quality["quality_score"] / 100.0
    if result["face_detected"]:
        # More faces successfully analyzed is a mild positive signal for
        # how much of the image the pipeline actually got to look at.
        quality_factor = min(1.0, quality_factor * (1.0 if result["face_count"] else 1.0))

    logger.info(
        "image pipeline_used=%s verdict=%s face_count=%d prob_real=%.4f quality_score=%.1f models_used=%s",
        result["pipeline_used"], result["verdict"], result["face_count"], result["prob_real"],
        quality["quality_score"], result["models_used"],
    )

    return {
        "prob_real": result["prob_real"],
        "verdict": result["verdict"],
        "pipeline_used": result["pipeline_used"],
        "face_detected": result["face_detected"],
        "face_count": result["face_count"],
        "faces": result["faces"],
        "artifact_scores": result["artifact_scores"],
        "models_used": result["models_used"],
        "disagreement": result["disagreement"],
        "quality": quality,
        "quality_factor": quality_factor,
        "warnings": result["warnings"] + quality["warnings"],
        "explanation": explanation,
        "explanation_image": result["explanation_image"],
        "ela_heatmap": result["ela_heatmap"],
    }
