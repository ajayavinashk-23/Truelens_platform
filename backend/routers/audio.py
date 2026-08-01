import time
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.audio_detector import predict_audio_bytes
from utils.file_validation import validate_upload
from utils.trust_score import build_report_fields
from utils.report_text import build_visual_indicators, summary_for, recommendations_for

router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.post("/analyze")
async def analyze_audio(file: UploadFile = File(...)):
    start = time.perf_counter()
    contents = await validate_upload(file, "audio")

    try:
        result = predict_audio_bytes(contents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Audio inference failed: {exc}") from exc

    fields = build_report_fields(result["prob_real"], media_type="Audio", quality_factor=result["quality_factor"])
    elapsed = time.perf_counter() - start

    indicators = build_visual_indicators("audio", fields["risk_level"])

    return {
        **fields,
        "processing_time": f"{elapsed:.1f} sec",
        "file_name": file.filename,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "segments": result["segments"],
        "suspicious_segments": result["suspicious_segments"],
        "quality": result["quality"],
        "warnings": result["warnings"],
        "summary": summary_for("audio", fields["risk_level"]),
        "visual_indicators": indicators,
        "potential_manipulation_indicators": [i["label"] for i in indicators if i["flagged"]],
        "recommendations": recommendations_for(fields["risk_level"]),
    }
