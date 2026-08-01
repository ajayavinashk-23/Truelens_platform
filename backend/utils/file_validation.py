from fastapi import HTTPException, UploadFile

LIMITS = {
    "image": {
        "content_types": {"image/jpeg", "image/png", "image/webp"},
        "max_mb": 25,
    },
    "video": {
        "content_types": {"video/mp4", "video/quicktime"},
        "max_mb": 200,
    },
    "audio": {
        "content_types": {"audio/wav", "audio/x-wav", "audio/mpeg"},
        "max_mb": 50,
    },
}


async def validate_upload(file: UploadFile, media_type: str) -> bytes:
    """Reads the file into memory after checking content-type and size."""
    rules = LIMITS[media_type]

    if file.content_type not in rules["content_types"]:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type '{file.content_type}' for {media_type} analysis.",
        )

    contents = await file.read()
    max_bytes = rules["max_mb"] * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {rules['max_mb']}MB limit for {media_type} analysis.",
        )

    return contents
