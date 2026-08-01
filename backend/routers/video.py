import time
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.video_detector import predict_video_bytes
from utils.file_validation import validate_upload
from utils.trust_score import build_report_fields
from utils.report_text import build_visual_indicators, summary_for, recommendations_for

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    start = time.perf_counter()
    contents = await validate_upload(file, "video")

    try:
        result = predict_video_bytes(contents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Video inference failed: {exc}") from exc

    face_detected = result["face_detected"]
    fields = build_report_fields(
        result["prob_real_avg"], media_type="Video", quality_factor=result.get("valid_ratio", 1.0)
    )
    elapsed = time.perf_counter() - start

    indicators = build_visual_indicators("video", fields["risk_level"], face_detected=face_detected)

    return {
        **fields,
        "processing_time": f"{elapsed:.1f} sec",
        "file_name": file.filename,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "face_detected": face_detected,
        "face_detected_ratio": result["face_detected_ratio"],
        "frames_analyzed": result["frame_count_analyzed"],
        "frames_skipped": result["frames_skipped"],
        "suspicious_timestamps": result["suspicious_timestamps"],
        "warnings": result["warnings"],
        "summary": summary_for("video", fields["risk_level"], face_detected=face_detected),
        "visual_indicators": indicators,
        "potential_manipulation_indicators": [i["label"] for i in indicators if i["flagged"]],
        "recommendations": recommendations_for(fields["risk_level"]),
        "frame_analysis": {
            "frame_count_analyzed": result["frame_count_analyzed"],
            "frames_skipped": result["frames_skipped"],
            "timeline": result["timeline"],
            "suspicious_timestamps": result["suspicious_timestamps"],
        },
    }
