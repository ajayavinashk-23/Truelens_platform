import time
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.image_detector import predict_image_bytes
from utils.file_validation import validate_upload
from utils.trust_score import build_report_fields
from utils.report_text import build_visual_indicators, summary_for, recommendations_for

router = APIRouter(prefix="/api/image", tags=["image"])


@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    start = time.perf_counter()
    contents = await validate_upload(file, "image")

    try:
        result = predict_image_bytes(contents)
    except ValueError as exc:
        # Rejected input (corrupted / too small / unusably blurry) — a
        # client error, not a server error.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Image inference failed: {exc}") from exc

    face_detected = result["face_detected"]
    fields = build_report_fields(result["prob_real"], media_type="Image", quality_factor=result["quality_factor"])
    elapsed = time.perf_counter() - start

    indicators = build_visual_indicators("image", fields["risk_level"], face_detected=face_detected)

    explanation_image = result.get("explanation_image") or {}

    return {
        **fields,
        "processing_time": f"{elapsed:.1f} sec",
        "file_name": file.filename,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "face_detected": face_detected,
        "face_count": result["face_count"],
        "faces": result["faces"],
        "pipeline_used": result["pipeline_used"],
        "ensemble_verdict": result["verdict"],
        "models_used": result["models_used"],
        "artifact_scores": result["artifact_scores"],
        "detector_disagreement": result["disagreement"],
        "ela_heatmap": result.get("ela_heatmap"),
        "quality_score": result["quality"]["quality_score"],
        "blur_score": result["quality"]["blur_score"],
        "brightness": result["quality"]["brightness"],
        "contrast": result["quality"]["contrast"],
        "resolution": {"width": result["quality"]["width"], "height": result["quality"]["height"]},
        "warnings": result["warnings"],
        "explanation": result["explanation"],
        "heatmap": explanation_image.get("heatmap"),
        "heatmap_overlay": explanation_image.get("overlay"),
        "summary": summary_for("image", fields["risk_level"], face_detected=face_detected),
        "visual_indicators": indicators,
        "potential_manipulation_indicators": [i["label"] for i in indicators if i["flagged"]],
        "recommendations": recommendations_for(fields["risk_level"]),
    }
